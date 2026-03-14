# Changelog - Crypto Quant AI Bot

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
