# src/data_fetcher.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class DataFetcher:
    @staticmethod
    def get_historical_data(ticker: str, start: str = None, end: str = None, period: str = "5y") -> pd.DataFrame:
        """
        주식의 과거 데이터를 가져옵니다. 
        start와 end가 제공되면 해당 기간의 데이터를, 아니면 period 기준 데이터를 가져옵니다.
        """
        stock = yf.Ticker(ticker)
        
        if start and end:
            df = stock.history(start=start, end=end)
        elif start:
            # start가 있고 end가 없으면 start부터 현재까지
            df = stock.history(start=start)
        else:
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
