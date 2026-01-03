# src/analyzer.py
import pandas as pd
import numpy as np

class MarketAnalyzer:
    @staticmethod
    def calculate_statistics(df: pd.DataFrame, window: int = 252) -> pd.DataFrame:
        """
        일일 등락률 및 등락률 기반 표준편차를 계산합니다. (이미지 방식)
        """
        # 일일 등락률 계산
        df['Return'] = df['Close'].pct_change()
        
        # 등락률의 이동 표준편차 (Volatility %)
        df['Vol_Std'] = df['Return'].rolling(window=window).std()
        
        # 이미지의 1, 2, 3표준편차 선 계산
        df['Std_Level_1'] = -df['Vol_Std']
        df['Std_Level_2'] = -df['Vol_Std'] * 2
        df['Std_Level_3'] = -df['Vol_Std'] * 3
        
        # 기존 Z-Score (가격 기준)도 유지
        df['SMA_Price'] = df['Close'].rolling(window=window).mean()
        df['STD_Price'] = df['Close'].rolling(window=window).std()
        df['Z_Score'] = (df['Close'] - df['SMA_Price']) / df['STD_Price']
        
        return df

    @staticmethod
    def run_backtest(df: pd.DataFrame, buy_quantity: int = 50):
        """
        이미지 내 테이블처럼 과거 데이터를 순회하며 가상 매수 시뮬레이션을 수행합니다.
        조건: 당일 등락률 < 1표준편차(Std_Level_1)
        """
        balance = 0
        total_quantity = 0
        total_investment = 0
        df['Buy_Signal'] = ""
        df['Buy_Qty'] = 0
        df['Buy_Amount'] = 0.0

        for i in range(1, len(df)):
            # 매수 조건: 등락률이 -1표준편차보다 낮을 때
            if not pd.isna(df['Std_Level_1'].iloc[i]) and df['Return'].iloc[i] < df['Std_Level_1'].iloc[i]:
                price = df['Close'].iloc[i]
                df.at[df.index[i], 'Buy_Signal'] = "매수"
                df.at[df.index[i], 'Buy_Qty'] = buy_quantity
                df.at[df.index[i], 'Buy_Amount'] = price * buy_quantity
                
                total_quantity += buy_quantity
                total_investment += (price * buy_quantity)

        return df, total_quantity, total_investment

    @staticmethod
    def get_target_price(sma: float, std: float, target_z: float) -> float:
        """
        특정 Z-Score에 해당하는 주가를 역산합니다.
        Price = SMA + (Z * STD)
        """
        if pd.isna(sma) or pd.isna(std):
            return 0.0
        return sma + (target_z * std)

    @staticmethod
    def get_signal(z_score: float, thresholds: dict) -> tuple:
        """
        Z-Score에 따른 매수 신호 단계를 반환합니다.
        """
        if pd.isna(z_score):
            return "WAIT", 0
            
        if z_score <= thresholds["LEVEL_3"]:
            return "PANIC BUY", 3
        elif z_score <= thresholds["LEVEL_2"]:
            return "STRONG BUY", 2
        elif z_score <= thresholds["LEVEL_1"]:
            return "BUY", 1
        
        return "WAIT", 0
