# Changelog - Crypto Quant AI Bot

## [2026-03-15] - Upgrade 0.1.5 (AI Memory & Interactive Flow)
### Added
- **AI Memory Persistent Buffer**: Created `ai_memory.json` to cache analysis results for multiple symbols.
- **AI Memory Lifecycle**: Implemented 60-minute freshness TTL and automatic garbage collection (cleans older than 24h or >50 entries).
- **Interactive Shortcut Flow**: `LLL` and `SSS` commands now support auto-analysis, trend confluence checks (Y/N prompt), and manual TP/SL input.
- **Smart Symbol Matching**: `BNB` now correctly matches `BNBUSDC` in the AI brain memory.
- **PIN-based Security**: Replaced API Key authentication for the "Dừng Bot" button with a customizable Mã PIN (default: 123456).
- **Robust Value Parsing**: Added `safe_extract_price` helper to handle non-numeric AI outputs (like price ranges).

### Changed
- **Default Leverage**: Adjusted to **15x** (ISOLATED).
- **Default Risk**: Risk parameter in commands now refers to raw USDT amount (Bot calculates final Volume using leverage).
- **Telegram Timeout**: Increased request timeouts to 30s to prevent analysis-related timeouts.

### Fixed
- **Binance Error -4509**: Fixed "Time in Force (TIF) GTE" error by using `quantity` + `reduceOnly=True` for SL/TP orders linked to LIMIT entries.
- **ValueError**: Resolved price conversion crash when AI provided price ranges instead of single numbers.
- **Leverage Consistency**: Cleaned up inconsistent leverage logic in `execute_conditional_order`.
- **NameError**: Restored missing `logger` definition in `telegram_ctrl.py`.

## [2026-03-15] - Upgrade 0.1.4 (AI Intelligence & SDK Upgrade)
### Added
- **Candlestick Pattern Intelligence:** Tích hợp kiến thức mô hình nến theo chuẩn **Thomas Bulkowski** vào System Prompt của AI. Bot hiện biết **Performance Rank** của từng mô hình nến để đưa ra kết luận hội tụ (Triple Confluence).
- **Algorithmic Pattern Detection:** Thêm `pandas_ta.cdl_pattern` vào `ta_calculator.py` để tự động nhận diện Engulfing, Hammer, ShootingStar, MorningStar, EveningStar bằng thuật toán.
- **Candlestick Knowledge Base:** Tạo `docs/strategies/candlestick_patterns.md` làm tài liệu huấn luyện AI.

### Changed
- **Gemini SDK Upgrade:** Chuyển từ package `google.generativeai` (đã khai tử) sang `google.genai` v1.60.0 (SDK mới chính thức). Model name đổi sang prefix `models/` (ví dụ: `models/gemini-3.1-pro-preview`).
- **FastAPI Modernization:** Thay thế `@app.on_event` (deprecated) bằng `lifespan` context manager (chuẩn mới nhất 2025).

### Fixed
- **Binance API 2026 Support:** Khắc phục lỗi API -4120 & -1102 bằng cách triển khai endpoint `/fapi/v1/algoOrder` cho các lệnh STOP_MARKET/TAKE_PROFIT_MARKET.
- **Precision Order Type:** Chuyển đổi lệnh `/trade` từ MARKET sang LIMIT để đảm bảo bot khớp lệnh đúng giá Entry người dùng yêu cầu.
- **Telegram Command Recognition:** Gỡ bỏ bộ lọc `COMMAND` để bot có thể nhận diện các lệnh gõ trực tiếp thay vì chỉ copy-paste từ tin nhắn hỗ trợ.
- **Windows aiodns Bug:** Thêm `asyncio.WindowsSelectorEventLoopPolicy()` vào `data_ingestion.py`.
- **NameError logger:** Phục hồi `setup_global_logging()` và `logger` về đúng vị trí module-level trong `main.py`.
- **Centralized Client:** Sử dụng `BinanceClientManager` để quản trị phiên kết nối tập trung, sửa lỗi rò rỉ phiên (`Unclosed client session`).

### Added
- **Customizable Risk:** Hỗ trợ tham số `RISK` (số tiền USDT muốn rủi ro) trực tiếp trong các lệnh Telegram.

1: 
2: ## [2026-03-15] - Upgrade 0.1.3 (Security & Performance Hardening)
3: ### Added
4: - **API Security:** Triển khai Header `X-API-KEY` bảo vệ các endpoint Dashboard nhạy cảm.
5: - **Environment Protection:** Thêm file `.gitignore` để ngăn chặn lộ file `.env` chứa API Keys.
6: - **Tail Log Implementation:** Nâng cấp API `/api/logs` sử dụng kỹ thuật "Tail" (đọc ngược), giúp server cực nhẹ ngay cả khi file log lớn hàng GB.
7: 
8: ### Changed
9: - **Production Ready Config:** Tắt chế độ `reload` và giới hạn `host="127.0.0.1"` để tăng cường bảo mật server.
10: - **Connection Pooling:** Refactor `data_ingestion.py` sử dụng `BinanceClientManager` để tái sử dụng connection tới Binance, giảm độ trễ và tránh bị Rate Limit.
11: - **Modular Imports:** Di chuyển tất cả các `import` lên đầu file `main.py` để tối ưu hóa performance nạp module.
12: 
13: ### Fixed
14: - **OOM Prevention:** Loại bỏ nguy cơ tràn bộ nhớ RAM khi người dùng mở Dashboard xem log trong thời gian dài.
15: 

## [2026-03-14] - Upgrade 0.1.2 (Stability & UX)
### Added
- **Slash Commands Support:** Hệ thống Telegram Bot hỗ trợ linh hoạt các lệnh `/scan`, `/trade`, `/limit`, `/status`, `/orders`, `/help`.
- **Wallet Status:** Lệnh `/status` hiển thị số dư ví Futures thực tế và chế độ giao dịch.
- **AI Brain Dashboard:** Trang Web Dashboard tích hợp `marked.js` để hiển thị báo cáo phân tích Markdown chuyên nghiệp.
- **Dynamic Symbol Sync:** Biểu đồ Web tự động nhảy mã (Symbol) dựa trên báo cáo AI mới nhất.

### Changed
- **Uvicorn Optimization:** Loại bỏ thư mục `logs/` khỏi trình giám sát `reload` để tránh vòng lặp khởi động vô hạn.
- **AI Prompt Enforcement:** Ép AI tuân thủ nghiêm ngặt cấu trúc Markdown 4 phần của `xuhuong_gia.md`.

### Fixed
- **Infinite Loop Bug:** Sửa lỗi Terminal log bị rác hàng nghìn dòng "1 change detected".
- **Symbol Hardcoding:** Sửa lỗi Bot luôn đánh BTCUSDT dù user yêu cầu mã khác.
- **Missing Imports:** Sửa lỗi thiếu `os` và `json` trong một số module.
- **Telegram Conflict:** Tự động tắt các tiến trình cũ để tránh lỗi "Conflict" khi restart Bot.

## [2026-03-14] - Upgrade 0.1.1 (AI Intelligence)
### Added
- **AI MTFA Analysis:** Bot tự động xuất báo cáo đa khung thời gian chi tiết (bảng MTFA, Target Zones).
- **Professional Terminology:** Tích hợp bộ quy tắc phân tích kĩ thuật chuyên sâu (Magnet, Whipsaw, Confluence).
- **Enhanced Log Display:** Báo cáo chi tiết của AI được hiển thị trực tiếp trên Web Dashboard Terminal.

## [2026-03-14] - Release 0.1.0 Beta

### Added
- **Core Architecture:** Xây dựng khung xương dự án Modular (FastAPI + Async Tasks).
- **Binance Ingestion:** Module kéo dữ liệu nến Futures đa khung thời gian (4H, 1H, 15m).
- **Quant Calculation:** Tích hợp `pandas-ta` tính EMA, RSI, MACD, ADX, Bollinger Bands, ATR.
- **Telegram Router:** Bộ lọc Regex nhận diện 3 luồng: Tư vấn Ticker, Lệnh trực tiếp, Lệnh điều kiện.
- **AI Brain:** Tích hợp Gemini 3.1 Pro phân tích nến kết hợp Lượng tử (Multimodal).
- **Binance Executor:** Xử lý vào lệnh Market và lệnh chờ trigger (Stop-Loss-Limit).
- **Logging System:** Hệ thống ghi log xoay vòng 30 ngày (info.log & error.log).
- **Web Dashboard:** Giao diện theo dõi biểu đồ nến Live và Server Terminal Logs trực quan.

### Changed
- Cập nhật System Prompt AI yêu cầu hội tụ (confluence) của ít nhất 3 tham số kỹ thuật.
- Web UI tự động chuyển Ticker hiển thị khi có lệnh phân tích mới từ Telegram.

### Fixed
- Lỗi crash do Gemini trả về JSON dạng List.
- Lỗi hụt import `logging` trong module `binance_exec.py`.
- Lỗi KeyError do không nhất quán tên cột Pandas (Open vs open).
- Lỗi cache trình duyệt không load được script mới.
