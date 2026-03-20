CBX Trading Bot — Python FastAPI, PostgreSQL, Redis, python-binance SDK.

Giai đoạn 2 đã hoàn thành. Toàn bộ strategy pipeline hoạt động:
compression_detector → breakout_detector → expansion_validator
→ context_filter → risk_engine → entry_engine → trade_manager

Backtest Engine sẽ TÁI SỬ DỤNG các module trên — không viết lại logic.
Sự khác biệt duy nhất: thay vì fetch data realtime, load từ file/DB.
Thay vì gọi Binance API để đặt lệnh, dùng FillSimulator.

Yêu cầu bắt buộc:
1. TUYỆT ĐỐI không look-ahead bias — bar i chỉ được thấy bar 0..i
2. Decimal cho mọi số giá
3. Mỗi run ghi đầy đủ vào DB (RESEARCH_RUN + toàn bộ events + trades)
4. Slippage model phải configurable, không hardcode
5. Side LONG và SHORT test riêng biệt, không gộp