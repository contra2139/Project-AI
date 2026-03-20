import pandas as pd
import numpy as np
import sys
import os

# Thêm path để import backend/app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategy.feature_engine import FeatureEngine

def test_feature_engine():
    print("🚀 Đang chạy test cho Feature Engine...")
    
    # 1. Tạo dữ liệu giả lập (Synthetic Data)
    dates = pd.date_range(start="2024-01-01", periods=200, freq="15min")
    data = {
        'open': np.random.uniform(50000, 60000, 200),
        'high': np.random.uniform(50000, 60000, 200),
        'low': np.random.uniform(50000, 60000, 200),
        'close': np.random.uniform(50000, 60000, 200),
        'volume': np.random.uniform(10, 100, 200)
    }
    df = pd.DataFrame(data, index=dates)
    # Fix High/Low to be valid
    df['high'] = df[['open', 'close']].max(axis=1) + np.random.uniform(0, 100, 200)
    df['low'] = df[['open', 'close']].min(axis=1) - np.random.uniform(0, 100, 200)
    
    engine = FeatureEngine()
    
    # 2. Tính toán features
    print("Step 1: Calculating raw features...")
    df_with_features = engine.compute_features(df)
    
    # 3. Tính toán percentiles
    print("Step 2: Calculating percentiles (window=120)...")
    df_final = engine.calculate_percentiles(df_with_features)
    
    # 4. Kiểm tra output
    print("\n📊 Kết quả 5 nến cuối:")
    cols_to_show = ['close', 'atr_norm_pct', 'range_pct_pct', 'bb_width_pct', 'vol_ratio_pct']
    print(df_final[cols_to_show].tail())
    
    # Kiểm tra tính hợp lệ (Percentile phải từ 0-100)
    latest = df_final.iloc[-1]
    for col in ['atr_norm_pct', 'range_pct_pct', 'bb_width_pct', 'vol_ratio_pct']:
        val = latest[col]
        assert 0 <= val <= 100, f"Lỗi: {col} có giá trị {val} nằm ngoài dải 0-100"
        
    print("\n✅ Feature Engine hoạt động chính xác!")

if __name__ == "__main__":
    test_feature_engine()
