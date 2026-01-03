# src/data_fetcher.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class DataFetcher:
    @staticmethod
    def get_historical_data(ticker: str, period: str = "5y") -> pd.DataFrame:
        """
        주식의 과거 데이터를 가져옵니다. 
        기본적으로 2년치를 가져와서 252일 이평선을 계산할 수 있도록 합니다.
        """
        print(f"[{ticker}] 데이터 수집 중...")
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        if df.empty:
            print(f"Warning: {ticker} 데이터를 가져오지 못했습니다.")
            return pd.DataFrame()
            
        return df

    @staticmethod
    def get_current_price(ticker: str) -> float:
        """최신 종가를 가져옵니다."""
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return 0.0
