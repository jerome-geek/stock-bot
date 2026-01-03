# src/sheets_manager.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

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
        """이미지 레이아웃 최적화 (B2, B3 날짜 기록 포함)"""
        try:
            worksheet = self.spreadsheet.worksheet(ticker)
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=ticker, rows="2000", cols="20")

        # 1. 상단 요약 정보 (이미지 100% 재현)
        summary_data = [
            ["종목", ticker, "", "현재가", round(summary['current_price'], 2), "", "총 평가금액", round(summary['total_val'], 2), "", "매수횟수", summary['buy_count'], "", "종가 +", ""],
            ["시작날짜", summary['start_date'], "", "총 수량", summary['total_qty'], "", "총 수익금액", round(summary['total_profit'], 2), "", "최대 상승폭", f"{round(summary['max_gain']*100, 2)}%", "", "종가 -", ""],
            ["종료날짜", summary['end_date'], "", "총 매수금액", round(summary['total_invest'], 2), "", "총 평가수익률", f"{round(summary['roi']*100, 2)}%", "", "최대 하락폭", f"{round(summary['max_loss']*100, 2)}%", "", "1표준편차", f"{round(summary['s1']*100, 2)}%"],
            ["매수조건", f"{round(summary['s1']*100, 2)}%", "", "수익률 평균", f"{round(df['Return'].mean()*100, 3)}%", "", "표준편차", f"{round(summary['volatility']*100, 2)}%", "", "", "", "", "2표준편차", f"{round(summary['s2']*100, 2)}%"],
            ["매수수량", 100, "", "", "", "", "", "", "", "", "", "", "3표준편차", f"{round(summary['s3']*100, 2)}%"],
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
        
        worksheet.update("A7", [table_header] + rows)
        
        # 날짜 포맷 힌트 제공
        worksheet.update_note("B2", "YYYY-MM-DD 형식으로 입력 후 봇을 실행하세요.")
        worksheet.format("A1:N5", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"})
        worksheet.format("A7:F7", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8}})

    def update_dashboard(self, summary_list):
        """메인 대시보드 요약 정보 업데이트"""
        try:
            worksheet = self.spreadsheet.worksheet("Dashboard")
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title="Dashboard", rows="50", cols="15")

        header = [
            "Ticker", "Current Price", "Z-Score", "Signal", 
            "1차 매수가(-1σ)", "2차 매수가(-2σ)", "3차 매수가(-3σ)", 
            "Last Updated"
        ]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        rows = []
        for item in summary_list:
            rows.append([
                item['ticker'],
                round(item['current_price'], 2),
                round(item['z_score'], 3) if not pd.isna(item['z_score']) else "N/A",
                item['signal'],
                round(item['target_1'], 2),
                round(item['target_2'], 2),
                round(item['target_3'], 2),
                now
            ])
        
        worksheet.clear()
        worksheet.update([header] + rows)
