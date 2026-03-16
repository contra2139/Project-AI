import pandas as pd
import numpy as np

def detect_msl(df: pd.DataFrame) -> dict:
    """
    Phân tích Cấu trúc thị trường (Market Structure) và Thanh khoản (Liquidity).
    Trả về: { market_structure, fvg_zones, trend_strength }
    """
    if df.empty or len(df) < 50:
        return {"structure": "UNKNOWN", "fvgs": [], "strength": 0}

    # 1. Nhận diện Đỉnh/Đáy (Swing High/Low) đơn giản
    # Sử dụng window=5 để tìm các điểm xoay chiều
    df['swing_high'] = df['high'][(df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(2)) & 
                                 (df['high'] > df['high'].shift(-1)) & (df['high'] > df['high'].shift(-2))]
    df['swing_low'] = df['low'][(df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(2)) & 
                               (df['low'] < df['low'].shift(-1)) & (df['low'] < df['low'].shift(-2))]

    # Lấy danh sách các đỉnh đáy gần nhất
    recent_highs = df['swing_high'].dropna().tail(3).tolist()
    recent_lows = df['swing_low'].dropna().tail(3).tolist()

    structure = "RANGING"
    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
            structure = "BULLISH (HH-HL)"
        elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
            structure = "BEARISH (LH-LL)"

    # 2. Nhận diện Fair Value Gap (FVG)
    # FVG Bullish: Low(n) > High(n-2)
    # FVG Bearish: High(n) < Low(n-2)
    fvgs = []
    for i in range(2, len(df)):
        # Bullish FVG
        if df['low'].iloc[i] > df['high'].iloc[i-2]:
            gap_top = df['low'].iloc[i]
            gap_bottom = df['high'].iloc[i-2]
            fvgs.append({"type": "BULLISH", "top": gap_top, "bottom": gap_bottom, "size": gap_top - gap_bottom})
        
        # Bearish FVG
        if df['high'].iloc[i] < df['low'].iloc[i-2]:
            gap_top = df['low'].iloc[i-2]
            gap_bottom = df['high'].iloc[i]
            fvgs.append({"type": "BEARISH", "top": gap_top, "bottom": gap_bottom, "size": gap_top - gap_bottom})

    # Lấy 3 FVG gần nhất
    recent_fvgs = fvgs[-3:] if fvgs else []

    # 3. Đánh giá sức mạnh xu hướng dựa trên ADX và EMA (nếu có trong df)
    strength = 0
    if 'ADX_14' in df.columns:
        strength = df['ADX_14'].iloc[-1]

    return {
        "market_structure": structure,
        "recent_fvgs": recent_fvgs,
        "trend_strength_adx": round(strength, 2)
    }
