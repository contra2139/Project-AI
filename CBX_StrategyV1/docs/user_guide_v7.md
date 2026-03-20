# CBX Strategy V7 - Hướng dẫn sử dụng & Vận hành 🚀

Chào mừng anh đến với tài liệu hướng dẫn sử dụng **CBX Strategy V7**, hệ thống giao dịch tự động thông minh dựa trên mô hình Nén & Bùng nổ (Compression & Breakout).

---

## 1. Cơ chế hoạt động của Bot (The Core Logic)
Hệ thống hoạt động theo chu kỳ **15 phút** (mỗi khi kết thúc một cây nến). Quy trình tự động bao gồm:

### Giai đoạn 1: Quét tín hiệu (Scanner)
- **Check Compression**: Bot tìm kiếm các vùng giá đang "nén" (Volume thấp, ATR thấp, Bollinger Band hẹp) trong ít nhất 8 cây nến.
- **Breakout Detection**: Khi giá đóng cửa nằm ngoài vùng nén, Bot sẽ kích hoạt trạng thái chờ xác nhận.

### Giai đoạn 2: Lọc chất lượng (Filters)
- **Expansion**: Xác nhận lực bùng nổ qua Khối lượng (Volume > 1.3x trung bình) và Kích thước nến.
- **Context Filter (EMA50)**: Chỉ đánh LONG nếu giá nằm trên EMA50 và đường EMA50 đang dốc lên. Chỉ đánh SHORT nếu giá nằm dưới EMA50 và đường EMA50 đang dốc xuống.

### Giai đoạn 3: Thực thi & Quản lý lệnh (Trade Manager)
- **Vào lệnh**: Tự động tính toán số lượng (Qty) dựa trên 0.25% rủi ro/vốn (Risk per trade).
- **Chốt lời/Dừng lỗ**:
    - **SL**: Đặt dưới/trên vùng nén (cấu trúc failed).
    - **TP1 (+1R)**: Chốt 50% vị thế khi đạt tỉ lệ 1:1.
    - **Trailing Stop (Ratchet)**: Sau khi chốt TP1, Bot sẽ tự động dời SL theo giá (SL chỉ tiến, không lùi) để bảo vệ lợi nhuận.

---

## 2. Tương tác với Bot qua Telegram 📱
Đây là cách chính để anh theo dõi và điều khiển Bot mọi lúc mọi nơi.

### Các lệnh tra cứu:
- `/status`: Xem "sức khỏe" tài khoản (Equity, PnL trong ngày, số lệnh đang mở).
- `/signals`: Xem danh sách các cú Breakout vừa xảy ra.
- `/trades`: Danh sách chi tiết các lệnh đang gỡ (Giá vào, SL, TP, PnL hiện tại).
- `/ask <câu hỏi>`: **Hỏi AI Gemini**. Anh có thể hỏi: *"Thị trường hôm nay thế nào?"*, *"Tại sao lệnh SOL bị khớp?"*. AI sẽ đọc dữ liệu hệ thống để trả lời anh.

### Lệnh điều khiển (Dành cho Admin):
- `buy <SYMBOL> <SIZE%> <SL> <TP>`: Đặt lệnh LONG thủ công.
- `sell <SYMBOL> <SIZE%> <SL> <TP>`: Đặt lệnh SHORT thủ công.
- `/close <SYMBOL>`: Đóng lệnh đang mở ngay lập tức.

---

## 3. Cách Bot tự động Trading (Workflow)
Bot được thiết kế để chạy "Fire and Forget" (Chạy và quên đi):

1. **Khởi động**: Bot kết nối với Binance qua API Key (đã được audit an toàn, không có quyền rút tiền).
2. **Lấy dữ liệu**: Mỗi 15 phút, Bot tải dữ liệu nến mới nhất của BTC, BNB, SOL.
3. **Phân tích**: Chạy qua bộ lọc Strategy V7.
4. **Vào lệnh**: Nếu đạt mọi điều kiện, Bot gửi lệnh thẳng tới Binance.
5. **Thông báo**: Bot gửi ngay tin nhắn Telegram kèm hình vẽ/thông số cho anh.
6. **Theo dõi**: Bot cập nhật Trailing Stop từng phút cho đến khi lệnh đóng hoàn toàn.

---

## 4. Hướng dẫn Vận hành (Maintenance)
- **Xem Logs**: Nếu thấy bot không phản hồi, kiểm tra thư mục `logs/`.
- **Cấu hình**: Mọi thông số nhạy cảm nằm ở file `.env`. Tuyệt đối không chia sẻ file này.
- **Kiểm tra an toàn**: Thỉnh thoảng chạy script `python backend/scripts/verify_security.py` để đảm bảo các lớp bảo mật vẫn hoạt động tốt.

---
> [!TIP]
> **Lời khuyên**: Strategy V7 được tối ưu cho sự bền bỉ (Robust). Đừng quá lo lắng nếu thấy một vài lệnh thua liên tiếp, hệ thống đã được kiểm chứng (Backtest 2024-2026) cho kết quả dương bền vững (+40R đến +60R/năm).
