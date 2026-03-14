# AI Brain Module 
import google.generativeai as genai
import json
import logging
import mplfinance as mpf
import pandas as pd
import os
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)

genai.configure(api_key=config.GEMINI_API_KEY)

# Khởi tạo mô hình (Dùng gemini-1.5-pro để phân tích nâng cao, hoặc flash cho tốc độ)
generation_config = {
  "temperature": 0.2, # Yêu cầu độ chính xác Quant cao
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json", # Ép Format JSON
}

model = genai.GenerativeModel(
  model_name="gemini-3.1-pro-preview",
  generation_config=generation_config,
)

def create_chart_image(df: pd.DataFrame, symbol: str, timeframe: str) -> str:
    """Tạo file ảnh nến K-line từ DataFrame và lưu ra file tạm."""
    if df.empty:
        return None
        
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/chart_{symbol}_{timeframe}_{int(datetime.now().timestamp())}.png"
    
    # Chỉ vẽ 60 nến gần nhất để Gemini dễ nhìn
    plot_df = df.tail(60)
    
    # Định dạng đồ thị màu Dark
    mc = mpf.make_marketcolors(up='#0ECB81', down='#F6465D', edge='inherit', wick='inherit', volume='in')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True, base_mpf_style='nightclouds')
    
    # Add EMA lines
    added_plots = [
        mpf.make_addplot(plot_df['EMA_34'], color='#FCD535', width=1),
        mpf.make_addplot(plot_df['EMA_89'], color='#1E90FF', width=1)
    ]
    
    mpf.plot(plot_df, type='candle', volume=True, style=s, addplot=added_plots, 
             title=f"{symbol} - {timeframe}", savefig=file_path)
             
    return file_path

async def generate_trading_decision(symbol: str, data_dict: dict) -> dict:
    """Đóng gói dữ liệu Đa khung thời gian và Chart Ảnh -> Đẩy cho Gemini."""
    
    # Lấy dòng nến mới nhất của mỗi khung
    latest_data = {}
    for tf, df in data_dict.items():
        if not df.empty:
            # Dropna để an toàn chuyển JSON
            row = df.iloc[-1].fillna(0).to_dict()
            # Convert timestamp về string
            row['timestamp'] = str(df.index[-1])
            latest_data[tf] = row
            
    payload_json = json.dumps(latest_data, indent=2)
    
    # Tạo ảnh chart khung 1H (Context)
    chart_path = create_chart_image(data_dict.get('1h', pd.DataFrame()), symbol, "1h")
    
    system_prompt = f"""
    Bạn là một chuyên gia Senior Crypto Quant Trading.
    Nhiệm vụ: Dựa vào dữ liệu Lượng tử (TA) đa khung thời gian sau đây và Hình ảnh đồ thị đính kèm, hãy quyết định giao dịch cho mã {symbol}.
    
    Quy tắc bắt buộc:
    1. XÁC NHẬN XU HƯỚNG: Tuyệt đối không được đánh ngược xu hướng (Trend) của khung 4H. Phải sử dụng cả EMA (34, 89, 200) và đường MACD khung 4H để xác nhận trend (Không chỉ dựa vào duy nhất 1 đường EMA).
    2. ĐIỂM VÀO LỆNH (ENTRY): Xác định rủi ro phân phối dòng tiền. Khung 1H phải có sự hội tụ (confluence) của ít nhất 2 yếu tố: RSI (Quá mua/Quá bán) hoặc Stochastic, kèm theo Bollinger Bands (Squeeze hoặc Bounce). Tuyệt đối không Fomo.
    3. XÁC NHẬN ĐỘNG LƯỢNG (MOMENTUM): Phân tích Volume và MACD Histogram ở khung 15m/1H để đánh giá xem lực đẩy (breakout) có đủ mạnh hay không.
    4. QUẢN TRỊ RỦI RO (SL): Stop-Loss (SL) MỚI VÀ ĐỘNG phải được tính bằng công thức: [Entry] ± (1.5 * ATR khung 15m).
    5. FORMAT: Trả về chuẩn JSON. "decision" chỉ được phép là: "LONG", "SHORT", hoặc "STAND BY". "reasoning" cần giải thích ngắn gọn bằng 1-2 câu lý do tại sao các chỉ số trên lại dẫn tới quyết định này.
    
    Dữ liệu định lượng (JSON):
    {payload_json}
    """
    
    try:
        # Chuẩn bị payload multimodal
        request_parts = [system_prompt]
        
        if chart_path and os.path.exists(chart_path):
            img = genai.upload_file(chart_path)
            request_parts.append(img)
            
        logger.info(f"🧠 Đang gọi Gemini suy luận cho {symbol}...")
        response = await model.generate_content_async(request_parts)
        
        # Cleanup file tạm
        if chart_path and os.path.exists(chart_path):
            os.remove(chart_path)
            
        return json.loads(response.text)
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy Gemini API: {e}")
        return {
            "decision": "ERROR", 
            "reasoning": f"Lỗi AI: {str(e)}"
        }
