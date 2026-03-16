# YÊU CẦU LẬP TRÌNH: CRYPTO QUANT & AI FUTURES TRADING SYSTEM

**Vai trò của bạn:** Chuyên gia Senior Python Developer & Crypto Quant Trading.
**Nhiệm vụ:** Viết mã nguồn hoàn chỉnh (Vibecode) cho hệ thống giao dịch tự động. Yêu cầu code tối ưu, Clean Code, chia module độc lập và ứng dụng triệt để Actionable Insights.

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)
- **Mục tiêu:** Xây dựng Bot phân tích tự động. User chỉ cần nhập Ticker (VD: `BNBUSDC`) qua Telegram, hệ thống sẽ chạy luồng **Multi-Timeframe Analysis**, tính toán TA, đẩy cho Google Gemini phân tích và ra quyết định giao dịch trên Binance Futures.
- **Ngôn ngữ lõi:** Python 3.10+

## 2. NGĂN XẾP CÔNG NGHỆ (TECH STACK)
- **Backend & API:** `FastAPI`, `uvicorn`
- **Exchange API:** `python-binance` (Futures API)
- **Data & TA:** `pandas`, `pandas-ta`, `numpy`
- **AI Engine:** `google-generativeai` (Gemini Pro/Flash)
- **Charting (Backend):** `plotly` hoặc `mplfinance` (Dùng để xuất ảnh Chart gửi AI)
- **Telegram Controller:** `python-telegram-bot` (v20+)
- **Web Frontend:** `HTML5`, `Vanilla JS`, `TailwindCSS` (Binance Theme), `Lightweight Charts`

## 3. CẤU TRÚC THƯ MỤC (MODULAR ARCHITECTURE)
Thiết lập thư mục gốc `crypto_ai_bot/` với cấu trúc sau:
* `.env`: Chứa API Keys, Tokens (Không commit).
* `config.py`: Load và validate biến môi trường.
* `main.py`: Entry point (Khởi chạy FastAPI & Telegram Bot).
* `core/data_ingestion.py`: Async Fetch OHLCV (Multi-Timeframe).
* `core/ta_calculator.py`: Feature Engineering với pandas-ta.
* `core/ai_brain.py`: Xây dựng JSON/Image Payload & Call Gemini API.
* `core/binance_exec.py`: Thực thi lệnh Futures (Market/Limit/OCO).
* `core/telegram_ctrl.py`: Lắng nghe Ticker từ user.
* `web/templates/index.html`: Giao diện chính.
* `web/static/`: Thư mục chứa CSS/JS.

## 4. YÊU CẦU CHI TIẾT TỪNG MODULE (CORE LOGIC)

### 4.1. Telegram Trigger & Data Ingestion
- **Minimalist UI:** User chỉ cần gửi text thuần (VD: `BNBUSDC`, `BTCUSDT`). Không cần cú pháp `/`.
- **Auto Multi-Timeframe:** Khi nhận Ticker, dùng `asyncio` kéo song song 100 nến K-lines gần nhất cho 3 khung thời gian:
  1. **Macro (4H):** Xác định Market Structure.
  2. **Context (1H):** Xác định Support/Resistance & Momentum.
  3. **Trigger (15m):** Xác định Entry/SL/TP.

### 4.2. Feature Engineering (TA Calculator)
Sử dụng `pandas-ta` tính toán ĐẦY ĐỦ các chỉ số sau cho CẢ 3 KHUNG THỜI GIAN:
- **Momentum:** `stochrsi(k=3, d=3, length=14, rsi_length=14)`, `macd(fast=12, slow=26, signal=9)`, `rsi(length=14)`.
- **Volume:** Dữ liệu Volume gốc, `sma(volume, 20)`, `vwap`.
- **Trend:** `ema(34)`, `ema(89)`, `ema(200)`, `adx(length=14)`.
- **Volatility:** `bbands(length=20, std=2)`, `atr(length=14)`.
- **Data Cleansing (Bắt buộc):** Chạy hàm xử lý rỗng (`.dropna()`, `.fillna(0)`) sau khi tính toán để loại bỏ các giá trị `NaN` do độ trễ của EMA/MACD gây ra, đảm bảo Payload JSON sạch sẽ.

### 4.3. AI Brain (Gemini Confluence Engine)
- **Multimodal Payload:** 1. Vẽ một biểu đồ (K-lines + EMA + BB) của khung 1H hoặc 15m thành file ảnh.
  2. Gom nhóm dữ liệu dòng nến cuối cùng (Latest Candlestick) của cả 3 khung (4H, 1H, 15m) cùng các chỉ số TA thành một chuỗi **JSON duy nhất**.
- **System Prompt:** Yêu cầu Gemini phân tích sự hội tụ (Confluence) giữa các khung thời gian. Không được đi ngược Trend của khung 4H. Sử dụng ATR của khung 15m để tính **Stop-loss động**.
- **Output Validation:** Ép Gemini trả về chuỗi JSON chuẩn định dạng:
  `{"decision": "LONG"|"SHORT"|"STAND BY", "entry": float, "stop_loss": float, "take_profit": float, "reasoning": "string"}`

### 4.4. Binance Executor & Web UI
- **Binance Executor:** Đặt đòn bẩy tự động. Xử lý lệnh Futures kèm Stop-loss / Take-profit.
- **Web UI:** Chạy chung port với FastAPI. Giao diện Dark Mode chuẩn Binance (`#181A20`, `#FCD535`, `#0ECB81`, `#F6465D`). Nhúng `Lightweight Charts` để hiển thị real-time chart và log nhận định của AI.

## 5. THÔNG SỐ BẢO MẬT & CẤU HÌNH (.env)
Yêu cầu file `config.py` đọc và bảo mật các biến sau:
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (Khóa chặt, chỉ nhận lệnh từ ID này)
- `GEMINI_API_KEY`
- `TRADE_MODE` (paper_trading / live)