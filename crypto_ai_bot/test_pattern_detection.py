import pandas as pd
import pandas_ta as ta
import sys
import os

# Thêm thư mục gốc vào path để import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.ta_calculator import calculate_ta

def test_patterns():
    print("🚀 Đang kiểm tra khả năng nhận diện mô hình nến...")
    
    # Tạo dữ liệu giả lập chuẩn cho Bullish Engulfing
    # Nến trước: Giảm (89 -> 85)
    # Nến sau: Tăng (84 -> 91) - Bao phủ toàn bộ nến trước
    opens   = [100]*200 + [89, 84]
    highs   = [102]*200 + [90, 92]
    lows    = [98]*200  + [84, 83]
    closes  = [99]*200  + [85, 91]
    vols    = [1000]*200 + [800, 1500]

    df = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': vols
    })
    
    # Thêm timestamp
    df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='1h')
    
    print(f"📊 Đã tạo DataFrame với {len(df)} nến.")
    
    # Chạy TA
    result_df = calculate_ta(df)
    
    print("\n✅ Các cột mới được tạo:")
    pattern_cols = [col for col in result_df.columns if col.startswith('CDL_')]
    for col in pattern_cols:
        count = (result_df[col] != 0).sum()
        status = "🔥 CÓ PHÁT HIỆN" if count > 0 else "❄️ Chưa phát hiện"
        print(f"- {col}: {count} lần ({status})")

    if pattern_cols:
        print("\n🎉 Phấn khởi quá! Hệ thống đã nhận diện được mô hình nến thuật toán.")
    else:
        print("\n⚠️ Cảnh báo: Không tìm thấy cột CDL_ trong kết quả.")

if __name__ == "__main__":
    test_patterns()
