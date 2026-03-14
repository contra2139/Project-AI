# TA Calculator Module
# Feature Engineering áp dụng chỉ báo TA, khử nhiễu (NaN)

import pandas as pd
import pandas_ta as ta

def calculate_ta(df: pd.DataFrame) -> pd.DataFrame:
    """Tính các chỉ báo Momentum, Volume, Trend, Volatility
    Bắt buộc xử lý dropna tại cuối hàm.
    """
    if df.empty:
        return df
        
    # TODO: Add MACD, RSI, VWAP, EMA, BB, ATR
    
    # Data Cleansing
    df.dropna(inplace=True)
    return df
