import pandas as pd
import pandas_ta as ta

def calculate_ta(df: pd.DataFrame) -> pd.DataFrame:
    """Tính các chỉ báo Momentum, Volume, Trend, Volatility
    Bắt buộc xử lý dropna tại cuối hàm.
    """
    if df.empty or len(df) < 200:
        return df # Cần đủ nến để tính EMA200
        
    # Tính toán Momentum
    df.ta.stochrsi(k=3, d=3, length=14, rsi_length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.rsi(length=14, append=True)
    
    # Tính toán Volume
    df.ta.sma(close='volume', length=20, append=True) # volume SMA
    df.ta.vwap(append=True)
    
    # Tính toán Trend
    df.ta.ema(length=34, append=True)
    df.ta.ema(length=89, append=True)
    df.ta.ema(length=200, append=True)
    df.ta.adx(length=14, append=True)
    
    # Tính toán Volatility
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.atr(length=14, append=True)

    # Nhận diện Mô hình nến (Professional Patterns)
    # CDL_ENGULFING, CDL_HAMMER, CDL_SHOOTINGSTAR, etc.
    patterns = ["engulfing", "hammer", "shootingstar", "morningstar", "eveningstar"]
    df.ta.cdl_pattern(name=patterns, append=True)
    
    # Data Cleansing: Bỏ qua N giá trị đầu tiên bị trễ do EMA200 và giữ lại các giá trị sạch
    df.dropna(inplace=True)
    
    # Fill các cột lỗi bất thường nếu MACD/ADX có issues
    df.fillna(0, inplace=True)
    
    return df
