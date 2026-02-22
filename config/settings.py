# config/settings.py

# 분석 대상 종목
TICKERS = ["SOXL", "TQQQ", "FNGU", "BULZ", "TSLA", "TSLL", "KORU"]

# 티커별 한글 종목명
TICKER_NAMES = {
    "SOXL": "반도체 3배",
    "TQQQ": "나스닥100 3배",
    "FNGU": "FANG+ 3배",
    "BULZ": "빅테크 3배",
    "TSLA": "테슬라",
    "TSLL": "테슬라 2배",
    "KORU": "한국 3배",
}

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
