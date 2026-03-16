# Changelog - Crypto Quant AI Bot

## [0.1.6] - 2026-03-15
### Added
- **Market Structure & Liquidity (MSL) Analyzer:** Tự động nhận diện BOS, CHoCH và FVG.
- **Portfolio PnL Tracking:** Hiển thị vị thế đang mở, PnL và ROI thời gian thực trên Dashboard.
- **Dark Matte Comfort Theme:** Giao diện tối ưu cho mắt, sử dụng font Outfit và neutral background.
- **Historical Backtest Engine:** Mô phỏng chiến lược EMA+RSI trên dữ liệu quá khứ.
- **System Documentation:** Cẩm nang `USER_GUIDE.md` và `LOGIC_DIAGRAM.md`.
- **Migration SDK:** Chuyển sang `google.genai` v1.60.0 mới nhất.
- **Close Position API:** Cho phép đóng lệnh nhanh bằng mã PIN từ Dashboard.

### Fixed
- Lỗi "Unclosed client session" triệt để bằng cơ chế delay 0.5s và đóng session theo thứ tự ưu tiên.
- Lỗi mount static files trong FastAPI khiến CSS không load được. (Gộp từ Phase 07)
- Sửa lỗi `ValueError` khi AI trả về dải giá thay vì con số đơn lẻ.

### Maintenance
- **Memory Merger:** Hợp nhất 2 thư mục `.brain` thành một bản duy nhất tại root dự án để đảm bảo tính nhất quán của AI.
- **Systemization:** Cập nhật tài liệu `README.md` và `CHANGELOG.md` chuẩn hóa theo version 0.1.6.

## [0.1.5] - 2026-03-14
### Added
- **AI Brain v1.1:** System Prompt MTFA chuyên sâu với Magnet, Whipsaw, Confluence.
- **Conditional Orders:** Hỗ trợ lệnh Stop-Market và Take-Profit qua Algo Order API.
- **Web Dashboard:** monitor.html (FileResponse) để bypass browser cache.

### Fixed
- Lỗi parse Telegram Markdown khi gặp ký tự bảng `|`.
- Lỗi `ReferenceError` trong JS khi truy cập biến trước khi khởi tạo.

## [0.1.0] - 2026-02-27
- Khởi tạo dự án: Cấu trúc Modular, tích hợp Telegram và Binance Futures cơ bản.
