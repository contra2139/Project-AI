# 📘 HƯỚNG DẪN SỬ DỤNG & CƠ CHẾ HOẠT ĐỘNG
## Crypto Quant AI Bot (v0.1.6)

Tài liệu này tóm tắt cách vận hành và mô hình tư duy của hệ thống giao dịch kết hợp Định lượng và Trí tuệ nhân tạo.

---

## 🚀 1. HƯỚNG DẪN NHANH (QUICK START)

### Lệnh Điều Khiển (Telegram)
*   **Phân tích nhanh:** Gõ tên mã (VD: `BTCUSDT` hoặc `/scan BTCUSDT`).
*   **Vào lệnh thị trường:** `/trade BTCUSDT LONG 65000 68000/63000 [RISK]`
*   **Đặt bẫy giá (Limit):** `/limit BNBUSDC LONG 600 605 650/580`
*   **Phím tắt (Shortcut):** `LLL BTCUSDT 65000` (Tự động lấy TP/SL từ AI).
*   **Kiểm tra:** `/status` (Số dư), `/orders` (Lệnh chờ), `/help` (Hướng dẫn).

### Giao Diện Dashboard
*   Truy cập: `http://127.0.0.1:8000`
*   Theo dõi PnL, ROI thời gian thực và log hệ thống.
*   Nút **Shutdown (Kill Switch)** yêu cầu mã PIN để dừng bot an toàn.

---

## 🧠 2. CHI TIẾT HOẠT ĐỘNG CỦA MÔ HÌNH (HYBRID QUANT-AI)

Mô hình hoạt động theo quy trình 4 bước khép kín để đảm bảo tính kỷ luật và bảo mật vốn.

### Bước 1: Thu thập đa chiều (Multi-Timeframe Ingestion)
Bot không bao giờ phân tích đơn khung. Dữ liệu nến được lấy đồng thời từ:
- **4H:** Xác định cấu trúc thị trường dài hạn (Xu hướng mẹ).
- **1H:** Tìm kiếm các vùng Fair Value Gap (FVG) và kháng cự/hỗ trợ.
- **15m:** Tối ưu hóa điểm vào lệnh để có tỷ lệ R:R (Risk/Reward) tốt nhất.

### Bước 2: Phân tích Định lượng (Quant Features)
Hệ thống sử dụng toán học để "gắn nhãn" cho thị trường bằng các chỉ số:
- **Trend Moving Averages:** EMA 34/89/200 xác định "trọng lực" của giá.
- **Momentum:** RSI & MACD phát hiện vùng quá mua/quá bán và phân kỳ.
- **Volatility:** ATR xác định khoảng cách đặt SL an toàn, tránh bị "quét râu" nến.
- **Market Structure (MSL):** Tự động phát hiện **BOS** (Break of Structure) và **CHoCH** (Change of Character).

### Bước 3: Visual Intelligence (Mắt thần AI)
Bot chụp ảnh biểu đồ (Chart Image) và vẽ sẵn các đường chỉ báo. Ảnh này giúp AI Gemini:
- Nhìn thấy các đường Trendline trực quan.
- Xác định các cụm nến (Candlestick Clusters) mà dữ liệu JSON đôi khi bỏ sót.
- Cảm nhận được "độ dốc" và sức mạnh của các đợt bùng nổ giá.

### Bước 4: Suy luận & Quản trị rủi ro (Gemini 3.1 Pro)
Dữ liệu số (Quant) + Dữ liệu ảnh (Visual) được đẩy vào AI để thực hiện logic:
1.  **Hội tụ (Confluence Check):** Chỉ kích hoạt **LONG/SHORT** khi có ít nhất 3 yếu tố ủng hộ (Ví dụ: Chạm EMA200 + RSI phân kỳ + Nến Hammer).
2.  **Kháng nghị (Correction):** Nếu User đặt lệnh thủ công ngược với xu hướng AI, hệ thống sẽ gửi cảnh báo yêu cầu xác nhận.
3.  **Lọc nhiễu:** Nếu thị trường đi ngang (Sideway) hoặc tín hiệu hỗn loạn, AI sẽ chọn **STAND BY**.

---

## 🛡️ 3. CƠ CHẾ BẢO VỆ TÀI KHOẢN

- **PIN-based Auth:** Mọi hoạt động nhạy cảm (Đóng lệnh, Tắt bot) đều cần mã PIN (.env).
- **Safe Value Parsing:** Tự động tính trung bình dải giá AI trả về để tránh lỗi đặt lệnh.
- **Async Cleanup:** Cơ chế tắt bot 3 giai đoạn (Telegram -> Binance -> Sockets) để tránh treo session và lỗi kết nối.
- **Memory Buffer:** Lưu trữ kết quả phân tích AI trong 60 phút để tiết kiệm Token và tăng tốc độ xử lý khi User gõ shortcut.

---
*Tài liệu này được cập nhật tự động bởi Antigravity AI.*
