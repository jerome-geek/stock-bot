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

    def get_history(self, ticker: str) -> pd.DataFrame:
        """기존 시트의 과거 종가를 DataFrame으로 반환합니다"""
        try:
            worksheet = self.spreadsheet.worksheet(ticker)
            records = worksheet.get_all_values()
            if len(records) > 12:
                headers = records[11]
                data = records[12:]
                
                # 최신순 정렬이므로, 오름차순(오래된 순)으로 변경
                data.reverse()
                df = pd.DataFrame(data, columns=headers)
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.dropna(subset=['Date']).set_index('Date')
                
                # Close 컬럼만 숫자로 파싱
                if 'Close' in df.columns:
                    df['Close'] = pd.to_numeric(df['Close'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    return df[['Close']]
        except Exception:
            pass
        return pd.DataFrame()

    def update_ticker_sheet(self, ticker: str, df: pd.DataFrame, summary: dict, new_rows_count: int = 0, update_last_row: bool = False):
        """종목 시트 업데이트 - 증분 업데이트 지원으로 기존 데이터 보존"""
        is_new_sheet = False
        try:
            worksheet = self.spreadsheet.worksheet(ticker)
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=ticker, rows="2000", cols="20")
            is_new_sheet = True

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
            ["", "", "", "", "", "", "", ""],  # 빈 줄
            ["매수조건", "", "", "매수가", "", "", "매수횟수", summary['buy_count']],
            ["1σ 매수", f"{round(summary['s1']*100, 2)}%", "", "", round(buy_price_1, 2), "", "최대 상승폭", f"{round(summary['max_gain']*100, 2)}%"],
            ["2σ 매수", f"{round(summary['s2']*100, 2)}%", "", "", round(buy_price_2, 2), "", "최대 하락폭", f"{round(summary['max_loss']*100, 2)}%"],
            ["3σ 매수", f"{round(summary['s3']*100, 2)}%", "", "", round(buy_price_3, 2), "", "", ""],
            ["매수수량", 100, "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", ""],  # 빈 줄
        ]
        
        # 요약 정보 업데이트
        worksheet.update("A1", summary_data)

        # 2. 상세 내역 (전체 기간, 최신순 정렬)
        table_header = ["Date", "Close", "등락률", "매수 여부", "매수 수량", "매수금액"]
        df_sorted = df.sort_index(ascending=False)
        
        if is_new_sheet:
            rows = []
            for index, row in df_sorted.iterrows():
                rows.append([
                    index.strftime('%Y-%m-%d'),
                    round(row['Close'], 2),
                    f"{round(row['Return']*100, 2)}%" if not pd.isna(row['Return']) else "0.00%",
                    row['Buy_Signal'] if 'Buy_Signal' in row else "",
                    row['Buy_Qty'] if 'Buy_Qty' in row and row['Buy_Qty'] > 0 else "",
                    round(row['Buy_Amount'], 2) if 'Buy_Amount' in row and row['Buy_Amount'] > 0 else ""
                ])
            worksheet.update("A12", [table_header] + rows)
            worksheet.update_note("B2", "YYYY-MM-DD 형식으로 입력 후 봇을 실행하세요.")
            worksheet.format("A1:H11", {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"})
            worksheet.format("A12:F12", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8}})
        else:
            # 기존 시트의 경우 증분 업데이트 수행
            if new_rows_count > 0:
                # 새로운 데이터만 추출하여 상단에 삽입
                df_new = df_sorted.head(new_rows_count)
                new_data = []
                for index, row in df_new.iterrows():
                    new_data.append([
                        index.strftime('%Y-%m-%d'),
                        round(row['Close'], 2),
                        f"{round(row['Return']*100, 2)}%" if not pd.isna(row['Return']) else "0.00%",
                        row['Buy_Signal'] if 'Buy_Signal' in row else "",
                        row['Buy_Qty'] if 'Buy_Qty' in row and row['Buy_Qty'] > 0 else "",
                        round(row['Buy_Amount'], 2) if 'Buy_Amount' in row and row['Buy_Amount'] > 0 else ""
                    ])
                # 13번째 행에 새 데이터 삽입
                worksheet.insert_rows(new_data, row=13)
                
            # 마지막 행(오늘) 업데이트
            if update_last_row:
                # 만약 new_rows_count가 삽입되었다면 기존 최상단 행은 13 + new_rows_count 임
                # 하지만 update_last_row가 True라면 최신 행 하나를 덮어씁니다 (혹은 insert 후라면 해당 row)
                last_row_index = 13
                latest_date_in_df = df_sorted.index[0]
                latest_row = df_sorted.iloc[0]
                updated_data = [[
                    latest_date_in_df.strftime('%Y-%m-%d'),
                    round(latest_row['Close'], 2),
                    f"{round(latest_row['Return']*100, 2)}%" if not pd.isna(latest_row['Return']) else "0.00%",
                    latest_row['Buy_Signal'] if 'Buy_Signal' in latest_row else "",
                    latest_row['Buy_Qty'] if 'Buy_Qty' in latest_row and latest_row['Buy_Qty'] > 0 else "",
                    round(latest_row['Buy_Amount'], 2) if 'Buy_Amount' in latest_row and latest_row['Buy_Amount'] > 0 else ""
                ]]
                # insert_rows를 했는지와 무관하게 13행에 현재 df의 가장 최신 데이터를 업데이트
                worksheet.update("A13:F13", updated_data)

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
                f"{current_price:.2f}({item['daily_change']*100:+.2f}%)",
                round(buy_price_1, 2),
                round(buy_price_2, 2),
                round(buy_price_3, 2),
                signal,
                now
            ])
        
        worksheet.clear()
        worksheet.update([header] + rows)
        worksheet.format("A1:H1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})
