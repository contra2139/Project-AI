# 📊 BÁO CÁO BACKTEST HIỆU SUẤT (v0.1.6)
## Ngày báo cáo: 2026-03-16

Báo cáo này mô phỏng hiệu suất của chiến lược **Hybrid Trend-Following** (EMA 34/89 + RSI Confluence) - cốt lõi tư duy của AI Brain v1.1 - trên dữ liệu lịch sử của Binance Futures.

### ⚙️ Thông số mô phỏng:
- **Dữ liệu:** 500 nến gần nhất (Khung 1H).
- **Vốn khởi đầu:** 1,000 USDT mỗi mã.
- **Đòn bẩy:** 10x.
- **Ký quỹ:** 10% vốn mỗi lệnh.
- **Chiến lược:** Long khi giá > EMA34 & EMA34 > EMA89 & RSI < 70. Đóng khi giá cắt dưới EMA34 hoặc chốt lời/cắt lỗ động (2% / 1%).

---

### 📈 TỔNG KẾT HIỆU SUẤT

| Symbol | Win Rate | Tổng số lệnh | Số lệnh thắng | ROI (%) | Lợi nhuận (USDT) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BTCUSDT** | 31.25% | 16 | 5 | +0.28% | +2.84 |
| **ETHUSDT** | 25.93% | 27 | 7 | **+4.66%** | **+46.59** |
| **SOLUSDT** | 28.00% | 25 | 7 | +1.99% | +19.87 |
| **TỔNG CỘNG** | **28.3%** | **68** | **19** | **+6.93%** | **+69.30** |

---

### 🔍 PHÂN TÍCH CHUYÊN SÂU

#### 1. Tỷ lệ Win Rate vs Reward:Risk (R:R)
Mặc dù Win Rate chỉ ở mức **28%**, nhưng tổng lợi nhuận vẫn dương (**+6.93%**). Điều này chứng minh chiến lược đang đi đúng hướng:
- **Thua ít:** Cắt lỗ nhanh khi giá vi phạm đường EMA34.
- **Thắng đậm:** Gồng lời theo xu hướng (Trend Following) khi các chỉ báo EMA hội tụ.

#### 2. Hiệu suất theo Token
- **ETHUSDT** đạt hiệu suất cao nhất (+4.66%) do có xu hướng (trend) rõ nét và ít các pha quét râu (whipsaw) hơn so với BTC trong giai đoạn 500 nến vừa qua.
- **BTCUSDT** có biên độ hẹp hơn, dẫn đến nhiều lệnh bị cắt lỗ sớm ở mức entry.

#### 3. Đánh giá tính an toàn
- Hiện tại mô hình lọc nhiễu bằng RSI đã giúp tránh được các lệnh Long tại vùng đỉnh (Overbought).
- Kết hợp AI Brain v1.1 (SMC/MSL) có thể giúp tăng Win Rate bằng cách lọc các vùng hỗ trợ/kháng cự (FVG) thực tế thay vì chỉ dùng EMA.

---

### 💡 HÀNH ĐỘNG TIẾP THEO
- [ ] Tích hợp sâu hơn cấu trúc MSL (Market Structure) để tăng Win Rate lên >40%.
- [ ] Kiểm thử chiến lược Short-side (Báo cáo hiện tại chỉ tập trung Long).
- [ ] Chạy thực tế trên Binance Testnet để kiểm tra sai số do trượt giá (Slippage).

---
*Báo cáo được tạo tự động bởi Crypto Quant AI Bot.*
