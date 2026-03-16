# AI Brain Module 
import google.genai as genai
from google.genai import types
import json
import logging
import mplfinance as mpf
import pandas as pd
import os
from datetime import datetime
from config import config
from core.msl_analyzer import detect_msl

logger = logging.getLogger(__name__)

client = genai.Client(api_key=config.GEMINI_API_KEY)

# Cấu hình generate (Yêu cầu độ chính xác Quant cao)
GENERATE_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    top_p=0.95,
    top_k=64,
    max_output_tokens=8192,
    response_mime_type="application/json",
)

MODEL_NAME = "models/gemini-3.1-pro-preview"

def create_chart_image(df: pd.DataFrame, symbol: str, timeframe: str) -> str:
    """Tạo file ảnh nến K-line từ DataFrame và lưu ra file tạm."""
    if df.empty:
        return None

    import os as _os
    _os.makedirs("temp", exist_ok=True)
    file_path = f"temp/chart_{symbol}_{timeframe}_{int(datetime.now().timestamp())}.png"

    # Chỉ vẽ 60 nến gần nhất để Gemini dễ nhìn
    plot_df = df.tail(60).copy()

    # mplfinance yêu cầu cột viết hoa (Open/High/Low/Close/Volume)
    # data_ingestion trả về lowercase → rename tạm trước khi vẽ
    col_map = {}
    for col in plot_df.columns:
        col_map[col] = col.capitalize()
    plot_df.rename(columns=col_map, inplace=True)

    # Định dạng đồ thị màu Dark
    mc = mpf.make_marketcolors(up='#0ECB81', down='#F6465D', edge='inherit', wick='inherit', volume='in')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True, base_mpf_style='nightclouds')

    # Thêm EMA (dùng tên đã capitalize)
    added_plots = []
    if 'Ema_34' in plot_df.columns:
        added_plots.append(mpf.make_addplot(plot_df['Ema_34'], color='#FCD535', width=1))
    if 'Ema_89' in plot_df.columns:
        added_plots.append(mpf.make_addplot(plot_df['Ema_89'], color='#1E90FF', width=1))

    kwargs = dict(type='candle', volume=True, style=s, title=f"{symbol} - {timeframe}", savefig=file_path)
    if added_plots:
        kwargs['addplot'] = added_plots

    mpf.plot(plot_df, **kwargs)
    return file_path

async def generate_trading_decision(symbol: str, data_dict: dict) -> dict:
    """Đóng gói dữ liệu Đa khung thời gian và Chart Ảnh -> Đẩy cho Gemini."""
    
    # Lấy dòng nến mới nhất của mỗi khung
    latest_data = {}
    for tf, df in data_dict.items():
        if not df.empty:
            # Phân tích Market Structure & Liquidity (MSL) cho khung này
            msl_result = detect_msl(df)
            
            # Đóng gói dữ liệu TA và MSL
            row = df.iloc[-1].fillna(0).to_dict()
            row['timestamp'] = str(df.index[-1])
            row['market_structure'] = msl_result.get('market_structure')
            row['recent_fvgs'] = msl_result.get('recent_fvgs')
            row['trend_strength_adx'] = msl_result.get('trend_strength_adx')
            
            latest_data[tf] = row
            
    payload_json = json.dumps(latest_data, indent=2)
    
    # Tạo ảnh chart khung 1H (Context)
    chart_path = create_chart_image(data_dict.get('1h', pd.DataFrame()), symbol, "1h")

    system_prompt = f"""
    Bạn là một Senior Crypto Quant Trader & Technical Analyst tại một quỹ đầu tư định lượng lớn.
    Nhiệm vụ: Phân tích kỹ thuật chuyên sâu (Technical Analysis) cho mã {symbol} dựa trên dữ liệu Quant đa khung thời gian (MTFA) và Hình ảnh đồ thị đính kèm.
    
    KIẾN THỨC CHUYÊN MÔN (PROFESSIONAL CANDLESTICK & SMC KNOWLEDGE):
    Bạn phải sử dụng kiến thức về các mô hình nến và Cấu trúc thị trường (Smart Money Concepts) để đối chiếu:
    - Market Structure: BOS (Break of Structure) và CHoCH (Change of Character). Đỉnh cao hơn (HH) và Đáy cao hơn (HL) xác nhận xu hướng Tăng.
    - Imbalance (FVG): Các khoảng trống Fair Value Gap là vùng giá thường được lấp đầy và đóng vai trò như Support/Resistance mạnh.
    - Bullish Engulfing: Performance Rank 22/103. Mạnh nhất khi xuất hiện tại Support hoặc vùng FVG Bullish.
    - Hammer: Performance Rank 26/103. Bóng nến dưới dài gấp đôi thân, báo hiệu kiệt sức lực bán.
    
    YÊU CẦU ĐỐI CHIẾU & LỌC NHIỄU:
    1. Quan sát ảnh Chart đính kèm để nhận diện Key Levels và cấu trúc thực tế trực quan.
    2. Đối chiếu với dữ liệu [market_structure] trong JSON. KHÔNG giao dịch ngược xu hướng 4H trừ khi có CHoCH rõ ràng.
    3. Tìm kiếm sự hội tụ (Confluence): Ví dụ Nến Hammer tại vùng FVG Bullish + RSI Oversold + Cấu trúc HH-HL.
    4. Nếu không có cấu trúc rõ ràng hoặc tín hiệu mâu thuẫn, hãy chọn "STAND BY".

    TÀI LIỆU HƯỚNG DẪN CẤU TRÚC BÁO CÁO (BẮT BUỘC TUÂN THỦ 100%):
    Báo cáo Markdown của bạn phải gồm 4 phần:
    
    # 📊 BÁO CÁO PHÂN TÍCH KỸ THUẬT & CHIẾN LƯỢC GIAO DỊCH: {symbol}
    
    ---
    
    ## I. TECHNICAL INDICATORS CHECKLIST
    *Đánh giá trạng thái hiện tại (Kết hợp Visual & Quant):*
    * **Price Action & Candlestick:** [Mô hình nến phát hiện được, Key Levels, Market Structure]
    * **EMA System (34, 89, 200):** [Vị trí giá so với EMA, Trend confirmation]
    * **Momentum (RSI/MACD):** [Overbought/Oversold, Divergence]
    * **Volume Confirmation:** [Sự xác nhận của khối lượng tại điểm đảo chiều]
    
    ---
    
    ## II. TREND DETERMINATION
    *Xác định xu hướng rõ ràng:*
    * **Major Trend (4H) & Minor Trend (1H):** [Bullish/Bearish/Sideway]
    * **Candlestick Confirmation:** [Mô hình nến có ủng hộ xu hướng hiện tại không?]
    
    ---
    
    ## III. ACTIONABLE TRADING STRATEGY
    | Vị thế (Position) | Điểm vào (Entry) | Chốt lời (TP) | Cắt lỗ (SL) |
    | :--- | :--- | :--- | :--- |
    | **[LONG/SHORT]** | **[Vùng giá]** | **[TP1 - TP2]** | **[Mốc dừng]** |
    
    ---
    
    ## IV. BOT DCA CONFIGURATION (IF APPLICABLE)
    [Cấu hình DCA % Deviation, Step, Vol Multiplier]
    
    YÊU CẦU FORMAT TRẢ VỀ (JSON):
    - Các trường "entry", "stop_loss", "take_profit" PHẢI là một CON SỐ DUY NHẤT (Ví dụ: "650.5", KHÔNG ĐƯỢC để dải giá như "650-655").
    {{
        "decision": "LONG" | "SHORT" | "STAND BY",
        "reasoning": "Giải thích logic: [Candlestick Pattern] + [TA Indicator] + [Trend].",
        "entry": "Giá Entry (Số duy nhất)",
        "stop_loss": "Giá Stop Loss (Số duy nhất)",
        "take_profit": "Giá Take Profit (Số duy nhất)",
        "report": "Chuỗi Markdown báo cáo 4 phần."
    }}
    
    Dữ liệu định lượng Real-time (Bao gồm CDL_Patterns):
    {payload_json}
    """
    
    try:
        # Chuẩn bị payload multimodal với google.genai SDK mới
        request_parts = [system_prompt]
        
        if chart_path and os.path.exists(chart_path):
            # Upload file ảnh
            with open(chart_path, 'rb') as f:
                image_bytes = f.read()
            request_parts.append(types.Part.from_bytes(data=image_bytes, mime_type='image/png'))
            
        logger.info(f"🧠 Đang gọi Gemini suy luận cho {symbol}...")
        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=request_parts,
            config=GENERATE_CONFIG,
        )
        
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
