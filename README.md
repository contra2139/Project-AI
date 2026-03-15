# Crypto Quant AI Bot 🤖

Bot giao dịch Crypto kết hợp phân tích kỹ thuật (Quant TA) và trí tuệ nhân tạo (Gemini 3.1 Pro).

## 🚀 Tính năng nổi bật
- **Phân tích đa khung thời gian:** Tự động kéo dữ liệu 4H, 1H, 15m từ Binance Futures.
- **Quant TA:** Tính toán EMA 34/89/200, RSI, MACD, ADX, Bollinger Bands, ATR.
- **AI Brain (Gemini 3.1 Pro):** Đưa ra quyết định dựa trên dữ liệu kỹ thuật kết hợp kiến thức mô hình nến của Thomas Bulkowski.
- **Telegram Control:** Điều khiển bot hoàn toàn qua Telegram với các lệnh linh hoạt.
- **Web Dashboard:** Theo dõi trực quan biểu đồ nến và log server thời gian thực.
- **Binance 2026 Ready:** Tương thích hoàn toàn với các thay đổi API mới nhất của Binance (Algo Orders).

## 🛠️ Cài đặt & Chạy
1. Cài đặt thư viện: `pip install -r requirements.txt`
2. Cấu hình file `.env` (xem `.env.example`).
3. Chạy bot: `python main.py`

## 📱 Lệnh Telegram
- `/scan [SYMBOL]` - AI phân tích xu hướng và đề xuất lệnh.
- `/trade [SYMBOL] [LONG/SHORT] [ENTRY] [TP]/[SL] [RISK]` - Vào lệnh LIMIT chính xác.
- `/limit [SYMBOL] [LONG/SHORT] [TRIGGER] [ENTRY] [TP]/[SL] [RISK]` - Đặt lệnh chờ kích hoạt.
- `/status` - Xem số dư ví Futures và trạng thái bot.
- `/orders` - Xem các lệnh đang treo trên sàn.
- `/help` - Xem hướng dẫn chi tiết.

## 🔒 Bảo mật
- API Keys được bảo vệ qua biến môi trường.
- Dashboard được bảo vệ bằng middleware `X-API-KEY`.
- Bot chỉ nhận lệnh từ đúng `TELEGRAM_CHAT_ID` của chủ nhân.
