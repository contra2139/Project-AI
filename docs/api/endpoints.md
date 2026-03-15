# API Documentation - Crypto Quant AI Bot

Ngày cập nhật: 2026-03-15
Base URL: `http://127.0.0.1:8000`

---

## 🔐 Security
Tất cả các endpoint API (trừ chart data cơ bản) đều yêu cầu Header:
- **Header:** `X-API-KEY`
- **Value:** [GEMINI_API_KEY] (Mã bảo mật của bạn)

---

## ── Backend Routes (FastAPI) ──

### GET `/`
- **Mô tả:** Trả về giao diện Web Dashboard (`monitor.html`).
- **Phản hồi:** HTML file.

### GET `/api/chart/{symbol}`
- **Mô tả:** Lấy dữ liệu nến (OHLCV) từ Binance Futures để vẽ biểu đồ.
- **Tham số:** 
    - `symbol` (string): Tên cặp giao dịch (VD: `BTCUSDT`).
    - `interval` (string, optional): Khung thời gian, mặc định `1h`.
- **Bảo mật:** Không yêu cầu (Public data).
- **Phản hồi:** JSON Array chứa các nến.

### GET `/api/ai_brain`
- **Mô tả:** Truy xuất kết quả phân tích AI chi tiết nhất được lưu trong `latest_ai.json`.
- **Bảo mật:** Cần `X-API-KEY`.
- **Phản hồi:** JSON object chứa `decision`, `reasoning`, `symbol`, và `report` (Markdown).

### GET `/api/logs`
- **Mô tả:** Đọc N dòng log cuối cùng từ file `app_info.log` bằng kỹ thuật đọc ngược (efficient tail).
- **Tham số:** `lines` (int, optional), mặc định 50.
- **Bảo mật:** Cần `X-API-KEY`.
- **Phản hồi:** JSON object `{ "logs": [...] }`.

### GET `/api/orders`
- **Mô tả:** Lấy danh sách các lệnh đang chờ (Open Orders) từ tài khoản Binance.
- **Bảo mật:** Cần `X-API-KEY`.
- **Phản hồi:** JSON object `{ "orders": [...] }`.
