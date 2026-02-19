# main.py
import sys
import pandas as pd
from datetime import datetime, timedelta
from config import settings, secrets_loader
from src.data_fetcher import DataFetcher
from src.analyzer import MarketAnalyzer
from src.sheets_manager import SheetsManager

def main():
    print("=== Stock Analysis Bot Start ===")
    
    # 1. 인증 정보 로드
    creds = secrets_loader.get_gcp_credentials()
    if not creds:
        print("Error: GCP 인증 정보(service_account.json)를 찾을 수 없습니다.")
        print("GCP 세팅 후 루트 폴더에 파일을 놓아주세요.")
        # 시트 매니저 없이 분석 결과만 출력하도록 진행 가능
        sheets = None
    else:
        sheets = SheetsManager(creds, settings.SPREADSHEET_NAME)
        print("Connected to Google Sheets.")

    summary_list = []

    # 2. 종목별 분석 수행
    for ticker in settings.TICKERS:
        try:
            # 시트에서 시작 날짜만 읽기 (end_date는 항상 오늘)
            start_date_str = None
            if sheets:
                start_date_str, _ = sheets.get_date_range(ticker)
            
            # 기본값 설정: 3년 전 ~ 오늘
            if not start_date_str:
                start_date_str = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')
            end_date_str = datetime.now().strftime('%Y-%m-%d')

            # 데이터 수집 (5년치 가져와서 필터링)
            df_full = DataFetcher.get_historical_data(ticker, period="5y")
            if df_full.empty:
                continue
            
            # 날짜 필터링
            df = df_full.loc[start_date_str:end_date_str].copy()
            if df.empty:
                print(f"[{ticker}] 해당 기간({start_date_str} ~ {end_date_str})에 데이터가 없습니다.")
                continue

            # 통계 분석 (이동평균윈도우는 설정 유지하되, 전체 기간의 표준편차 계산)
            df = MarketAnalyzer.calculate_statistics(df, window=settings.LOOKBACK_PERIOD)
            
            # 전체 기간 표준편차로 타점 안정화
            overall_std = df['Return'].std()
            df['Std_Level_1'] = -overall_std
            df['Std_Level_2'] = -overall_std * 2
            df['Std_Level_3'] = -overall_std * 3
            
            # 백테스트 실행 (수량 100주로 상향)
            df, total_qty, total_invest = MarketAnalyzer.run_backtest(df, buy_quantity=100)
            
            # 최신 상태 추출
            latest = df.iloc[-1]
            current_price = latest['Close']
            total_val = total_qty * current_price
            total_profit = total_val - total_invest
            roi = total_profit / total_invest if total_invest > 0 else 0
            
            ticker_summary = {
                'ticker': ticker,
                'current_price': float(current_price),
                'start_date': start_date_str,
                'end_date': end_date_str,
                'total_qty': int(total_qty),
                'total_invest': float(total_invest),
                'total_val': float(total_val),
                'total_profit': float(total_profit),
                'roi': float(roi),
                'volatility': float(overall_std),
                's1': float(-overall_std),
                's2': float(-overall_std * 2),
                's3': float(-overall_std * 3),
                'buy_count': int((df['Buy_Signal'] == "매수").sum()),
                'max_gain': float(df['Return'].max()),
                'max_loss': float(df['Return'].min()),
                'z_score': float(latest['Z_Score']) if not pd.isna(latest['Z_Score']) else 0.0,
                'signal': MarketAnalyzer.get_signal(latest['Z_Score'], settings.THRESHOLDS)[0],
                'target_1': float(MarketAnalyzer.get_target_price(latest['SMA_Price'], latest['STD_Price'], settings.THRESHOLDS["LEVEL_1"])),
                'target_2': float(MarketAnalyzer.get_target_price(latest['SMA_Price'], latest['STD_Price'], settings.THRESHOLDS["LEVEL_2"])),
                'target_3': float(MarketAnalyzer.get_target_price(latest['SMA_Price'], latest['STD_Price'], settings.THRESHOLDS["LEVEL_3"])),
                'daily_change': float(latest['Return']) if not pd.isna(latest['Return']) else 0.0,
            }
            summary_list.append(ticker_summary)
            
            print(f"[{ticker}] {start_date_str}~{end_date_str} 분석 완료. 수익률: {roi*100:.2f}%")

            if sheets:
                clean_df = df.replace([float('inf'), float('-inf')], 0).fillna(0)
                sheets.update_ticker_sheet(ticker, clean_df, ticker_summary)
                
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    # 3. 대시보드 업데이트
    if sheets and summary_list:
        sheets.update_dashboard(summary_list)
        print("Dashboard updated successfully.")
    
    # 4. 텔레그램 알림 전송
    if summary_list:
        from src.telegram_notifier import get_telegram_notifier
        telegram = get_telegram_notifier()
        if telegram:
            message = telegram.format_summary(summary_list)
            if telegram.send_message(message):
                print("Telegram notification sent.")
            else:
                print("Failed to send Telegram notification.")
        else:
            print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
    
    print("=== Stock Analysis Bot Done ===")

if __name__ == "__main__":
    main()
