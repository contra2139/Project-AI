import os
import sys

# Mock DATABASE_URL cho test (vì app.database sẽ được import)
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"

# Thêm đường dẫn backend vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from app.strategy.feature_engine import FeatureEngine
from app.strategy.compression_detector import CompressionDetector
from app.models.symbol import SymbolStrategyConfig
from datetime import datetime, timedelta

def generate_compression_data(n_bars=300):
    """Tạo dữ liệu giả lập có vùng nén."""
    dates = [datetime(2024, 1, 1) + timedelta(minutes=15*i) for i in range(n_bars)]
    
    # 1. Vùng bình thường (Biến động cao)
    data = {
        'open': np.random.uniform(50000, 50100, n_bars),
        'high': np.random.uniform(50100, 50200, n_bars),
        'low': np.random.uniform(49800, 49900, n_bars),
        'close': np.random.uniform(49900, 50100, n_bars),
        'volume': np.random.uniform(100, 500, n_bars)
    }
    
    # 2. Tạo vùng nén ở giữa (bar 100 đến 150)
    # Giảm biến động cực thấp
    for i in range(100, 150):
        data['high'][i] = 50010 + np.random.uniform(0, 5)
        data['low'][i] = 50000 - np.random.uniform(0, 5)
        data['close'][i] = 50005 + np.random.uniform(-2, 2)
        data['volume'][i] = 20 + np.random.uniform(0, 10)

    df = pd.DataFrame(data, index=dates)
    return df

def test_compression_detection():
    print("🚀 Bắt đầu test Compression Detector...")
    
    # Init Engine & Data
    engine = FeatureEngine()
    df_raw = generate_compression_data(300)
    
    # 1. Tính Features & Percentiles
    df_features = engine.compute_features(df_raw)
    df_final = engine.calculate_percentiles(df_features, window=100)
    
    # 2. Init Detector với Config mặc định
    config = SymbolStrategyConfig(
        atr_percentile_threshold=25.0,
        range_percentile_threshold=25.0,
        bb_width_percentile_threshold=25.0,
        volume_percentile_threshold=60.0,
        compression_min_bars=10,
        min_conditions_met=3
    )
    detector = CompressionDetector(config)
    
    # 3. Chạy phân tích
    events = detector.analyze_series(df_final, "BTCUSDT")
    
    print(f"📊 Tìm thấy {len(events)} vùng nén.")
    
    for i, ev in enumerate(events):
        print(f"\n--- Event {i+1} ---")
        print(f"Bắt đầu: {ev['start_time']}")
        print(f"Kết thúc: {ev.get('end_time', 'Đang diễn ra')}")
        print(f"Số nến: {ev['bar_count']}")
        print(f"Range Nén: {ev['low']:.2f} - {ev['high']:.2f}")
        print(f"Chất lượng (Avg Conditions): {ev['conditions_met_avg']:.2f}/4")
    
    assert len(events) > 0, "Lẽ ra phải tìm thấy ít nhất 1 vùng nén!"
    print("\n✅ Test Compression Detector thành công!")

if __name__ == "__main__":
    test_compression_detection()
