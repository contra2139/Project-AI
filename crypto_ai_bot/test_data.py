import asyncio
from core.data_ingestion import get_multi_timeframe_data
from core.ta_calculator import calculate_ta

async def main():
    print("🚀 Bắt đầu kéo dữ liệu từ Binance Futures...")
    symbol = "BTCUSDT"
    
    # 1. Kéo dữ liệu 3 khung thời gian (Cần limit lớn hơn 200 để tính EMA200)
    data = await get_multi_timeframe_data(symbol, limit=250)
    
    for tf, df in data.items():
        if df is None or df.empty:
            print(f"❌ Lỗi: Không kéo được dữ liệu khung {tf}")
            continue
            
        print(f"✅ Đã tải {len(df)} nến khung {tf}.")
        
        # 2. Xử lý TA
        print(f"⚙️ Đang tính TA cho khung {tf}...")
        df_ta = calculate_ta(df)
        
        print(f"👉 Số lượng nến SẠCH (sau khi bỏ NaN): {len(df_ta)}")
        # Cột MACD có tên biến động theo tham số, ta in các cột mới tính được
        print(f"📊 Dòng dữ liệu mới nhất khung {tf}:\n{df_ta.iloc[-1]}\n")

if __name__ == "__main__":
    asyncio.run(main())
