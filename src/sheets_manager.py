# src/sheets_manager.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
from config import settings

class SheetsManager:
    def __init__(self, credentials_info, spreadsheet_name):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, self.scope)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet_name = spreadsheet_name
        self.spreadsheet = self._get_or_create_spreadsheet()

    def _get_or_create_spreadsheet(self):
        # 1. ID가 설정되어 있다면 ID로 먼저 시도
        from config import settings
        if settings.SPREADSHEET_ID:
            try:
                return self.client.open_by_key(settings.SPREADSHEET_ID)
            except Exception as e:
                print(f"Error opening spreadsheet by ID: {e}")
        
        # 2. 이름으로 시도
        try:
            return self.client.open(self.spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            print(f"Spreadsheet '{self.spreadsheet_name}' not found. Creating new one...")
            return self.client.create(self.spreadsheet_name)

    def get_date_range(self, ticker: str):
        """시트에서 시작날짜와 종료날짜를 읽어옵니다. 없으면 기본값(3년전~오늘) 반환"""
        try:
            worksheet = self.spreadsheet.worksheet(ticker)
            start_date = worksheet.acell('B2').value
            end_date = worksheet.acell('B3').value
            return start_date, end_date
        except:
            return None, None

    def update_ticker_sheet(self, ticker: str, df: pd.DataFrame, summary: dict):
        """종목 시트 업데이트"""
        try:
            worksheet = self.spreadsheet.worksheet(ticker)
            worksheet.clear()  # 기존 데이터 초기화
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=ticker, rows="2000", cols="20")

        # 1. 상단 요약 정보
        ticker_name = settings.TICKER_NAMES.get(ticker, ticker)
        ticker_display = f"{ticker} / {ticker_name}"
        
        # 매수가 계산: 현재가 × (1 + 시그마%)
        current_price = summary['current_price']
        buy_price_1 = current_price * (1 + summary['s1'])
        buy_price_2 = current_price * (1 + summary['s2'])
        buy_price_3 = current_price * (1 + summary['s3'])
        
        summary_data = [
            ["종목", ticker_display, "", "현재가", round(current_price, 2), "", "총 평가금액", round(summary['total_val'], 2)],
            ["시작날짜", summary['start_date'], "", "총 수량", summary['total_qty'], "", "총 수익금액", round(summary['total_profit'], 2)],
            ["종료날짜", summary['end_date'], "", "총 매수금액", round(summary['total_invest'], 2), "", "총 평가수익률", f"{round(summary['roi']*100, 2)}%"],
            ["", "", "", "수익률 평균", f"{round(df['Return'].mean()*100, 3)}%", "", "표준편차", f"{round(summary['volatility']*100, 2)}%"],
            [],  # 빈 줄
            ["매수조건", "", "", "매수가", "", "", "매수횟수", summary['buy_count']],
            ["1σ 매수", f"{round(summary['s1']*100, 2)}%", "", "", round(buy_price_1, 2), "", "최대 상승폭", f"{round(summary['max_gain']*100, 2)}%"],
            ["2σ 매수", f"{round(summary['s2']*100, 2)}%", "", "", round(buy_price_2, 2), "", "최대 하락폭", f"{round(summary['max_loss']*100, 2)}%"],
            ["3σ 매수", f"{round(summary['s3']*100, 2)}%", "", "", round(buy_price_3, 2), "", "", ""],
            ["매수수량", 100, "", "", "", "", "", ""],
            [],  # 빈 줄
        ]
        
        # 기존 데이터 유지하며 업데이트 (날짜 입력 테스트를 위해 A1:N5만 업데이트)
        worksheet.update("A1", summary_data)

        # 2. 상세 내역 (전체 기간, 최신순 정렬)
        table_header = ["Date", "Close", "등락률", "매수 여부", "매수 수량", "매수금액"]
        rows = []
        df_sorted = df.sort_index(ascending=False)
        for index, row in df_sorted.iterrows():
            rows.append([
                index.strftime('%Y-%m-%d'),
                round(row['Close'], 2),
                f"{round(row['Return']*100, 2)}%" if not pd.isna(row['Return']) else "0.00%",
                row['Buy_Signal'],
                row['Buy_Qty'] if row['Buy_Qty'] > 0 else "",
                round(row['Buy_Amount'], 2) if row['Buy_Amount'] > 0 else ""
            ])
        
        worksheet.update("A12", [table_header] + rows)
        
        # 날짜 포맷 힌트 제공
        worksheet.update_note("B2", "YYYY-MM-DD 형식으로 입력 후 봇을 실행하세요.")
        worksheet.format("A1:H11", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"})
        worksheet.format("A12:F12", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8}})

    def update_dashboard(self, summary_list):
        """메인 대시보드 요약 정보 업데이트"""
        try:
            worksheet = self.spreadsheet.worksheet("Dashboard")
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title="Dashboard", rows="50", cols="15")

        header = [
            "분석일", "종목", "현재가", "1σ 매수가", "2σ 매수가", "3σ 매수가", 
            "Signal", "최종 업데이트"
        ]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        rows = []
        for item in summary_list:
            ticker = item['ticker']
            ticker_name = settings.TICKER_NAMES.get(ticker, ticker)
            ticker_display = f"{ticker} / {ticker_name}"
            
            # 매수가 계산: 현재가 × (1 + 시그마%)
            current_price = item['current_price']
            buy_price_1 = current_price * (1 + item['s1'])
            buy_price_2 = current_price * (1 + item['s2'])
            buy_price_3 = current_price * (1 + item['s3'])
            
            # Signal: 1σ 기준 (현재가가 1σ 매수가 이하면 매수)
            signal = "매수" if current_price <= buy_price_1 else "관망"
            
            rows.append([
                today,
                ticker_display,
                round(current_price, 2),
                round(buy_price_1, 2),
                round(buy_price_2, 2),
                round(buy_price_3, 2),
                signal,
                now
            ])
        
        worksheet.clear()
        worksheet.update([header] + rows)
        worksheet.format("A1:H1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})
