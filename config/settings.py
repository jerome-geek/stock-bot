# config/settings.py

# 분석 대상 3배 레버리지 ETF 종목
TICKERS = ["SOXL", "TQQQ", "FNGU", "BULZ"]

# 분석 설정
# 제도권주식분석 채널 전략: 1년(252 영업일) 기준 표준편차
LOOKBACK_PERIOD = 252

# 매수 신호 임계값 (Z-Score 기준)
THRESHOLDS = {
    "LEVEL_1": -1.0,  # 1차 매수 (관심)
    "LEVEL_2": -2.0,  # 2차 매수 (강력)
    "LEVEL_3": -3.0   # 3차 매수 (패닉)
}

# 구글 스프레드시트 설정
# URL: https://docs.google.com/spreadsheets/d/[이부분이_ID입니다]/edit
SPREADSHEET_ID = "17BUNcyaiUBzDgPMnafvY9ky9gDllQyvry-QEEXDJl78" # 여기에 시트 ID를 입력하면 더 안정적으로 작동합니다.
SPREADSHEET_NAME = "Stock_Bot_Dashboard"
