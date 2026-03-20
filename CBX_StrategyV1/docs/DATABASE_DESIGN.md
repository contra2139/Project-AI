# 📊 DATABASE DESIGN: CBX Strategy V1

Hệ thống lưu trữ được thiết kế để phục vụ triết lý **Research-first**, cho phép tái hiện (reproduce) mọi kết quả và audit sâu từng quyết định của bot.

---

## 1. Nhóm Quản Lý Chạy (Research & Config)

### ⚙️ SYMBOL_CONFIG
Lưu thông số sàn giao dịch, đảm bảo logic không bị hardcode.
- `symbol`: Tên cặp (BTCUSDC, ...)
- `lot_size_step`: Bước khối lượng tối thiểu
- `price_tick_size`: Bước giá tối thiểu
- `maker_fee`: Phí maker (%)
- `taker_fee`: Phí taker (%)
- `default_leverage`: Đòn bẩy mặc định

### 🚀 RESEARCH_RUN
Bảng trung tâm để quản lý các phiên chạy (Backtest/Live).
- `run_id`: Định danh duy nhất
- `start_time`: Thời điểm bắt đầu
- `mode`: `BACKTEST` / `PAPER` / `LIVE`
- `param_snapshot`: TOÀN BỘ config (JSON) tại thời điểm đó (ATR_period, thresholds, risk_pct...)
- `git_commit`: Hash code để biết chạy với phiên bản nào

---

## 2. Nhóm Sự Kiện (Event Study)

### 📦 COMPRESSION_EVENT
Ghi lại mọi vùng nén biến động.
- `event_id` (PK)
- `run_id` (FK)
- `symbol`, `timeframe`
- `start_time`, `end_time`
- `high`, `low`, `width_pct`
- `atr_percentile`, `range_percentile`, `bb_width_percentile`, `vol_percentile`

### ⚡ BREAKOUT_EVENT
Ghi lại khi giá phá vỡ vùng nén.
- `breakout_id` (PK)
- `event_id` (FK)
- `time`
- `side`: `LONG`/`SHORT`
- `price`
- `vol_ratio`: (Breakout volume / SMA20)
- `body_to_range`: Tỷ lệ thân nến

### 🔭 EXPANSION_EVENT (Tách rời)
Phân tích tính xác thực của breakout (Avoid false breakout).
- `expansion_id` (PK)
- `breakout_id` (FK)
- `is_confirmed`: True/False
- `confirmation_bar_index`: Phá vỡ được xác nhận sau bao nhiêu nến (1-3)
- `max_extension_atr`: Giá đi xa nhất sau breakout (tính theo ATR)
- `reentry_depth_pct`: Độ sâu khi quay lại vùng nén (nếu có)

---

## 3. Nhóm Vận Hành (Trades & Risk)

### 💰 TRADE
Lưu kết quả tổng hợp của một giao dịch.
- `trade_id` (PK)
- `expansion_id` (FK)
- `entry_model`: `FOLLOW_THROUGH` / `RETEST`
- `entry_price`
- `position_size`
- `total_pnl_r`: Lợi nhuận tính theo R
- `total_pnl_usd`: Lợi nhuận tính theo đô la (mới bổ sung)
- `status`: `OPEN` / `CLOSED` / `CANCELLED`

### 🚪 EXIT_EVENT (Chi tiết)
Theo dõi lộ trình thoát lệnh (Partial/Trailing).
- `exit_id` (PK)
- `trade_id` (FK)
- `time`
- `exit_type`: `PARTIAL_1R` / `TRAILING` / `STOP_LOSS` / `TIME_STOP`
- `price`, `size_closed`, `pnl_realized`

### 🛡️ SESSION_STATE
Persist trạng thái Risk Engine qua các lần khởi động.
- `session_id` (PK)
- `current_daily_pnl_r`
- `consecutive_failures`
- `trading_halted`: Boolean
- `halt_reason`: Lý do dừng

---

## 4. Nhóm Debug (The "Eyes" of Bot)

### 🔍 FILTER_LOG
"Đôi mắt" để biết tại sao bot CỰ TUYỆT một cơ hội.
- `log_id` (PK)
- `event_id` (FK)
- `filter_name`: `EMA50_DIRECTION`, `VOL_SPIKE_PRE_BREAK`, `WICK_DOMINANCE`, etc.
- `value_at_time`: Giá trị thực đo được
- `threshold`: Ngưỡng bị loại
- `decision`: `REJECTED`
