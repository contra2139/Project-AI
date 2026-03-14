# AI Brain Module 
# Đóng gói JSON Payload, Chart Image và gọi Gemini API
import google.generativeai as genai
from config import config

genai.configure(api_key=config.GEMINI_API_KEY)

async def generate_trading_decision(payload_json: str, chart_image_path: str = None):
    # TODO: Khởi tạo mô hình Gemini
    # TODO: System prompt cấm đi ngược Trend 4H + ép JSON output
    # TODO: Xử lý request multimodal (Text + Hình ảnh)
    pass
