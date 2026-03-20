# 📊 DATABASE DESIGN: CBX Strategy V3
# (Per-Symbol Strategy Architecture)

---

## Nguyên tắc thiết kế

1. Mỗi symbol có bộ tham số riêng, được lưu độc lập — không dùng chung config.
2. Hệ thống phải hỗ trợ thêm symbol mới mà không cần thay đổi code hay schema.
3. Mọi quyết định phải có dấu vết (trace) để audit được.
4. Mọi con số phải tái tính được từ raw data mà không cần chạy lại pipeline.
5. Không có logic ẩn ở bất kỳ đâu.

---

## Sơ đồ quan hệ tổng thể

```
SYMBOL_REGISTRY                     ← Danh sách tất cả symbol được quản lý
    │
    └── SYMBOL_EXCHANGE_CONFIG      ← Thông số kỹ thuật sàn (fee, tick size...)
    └── SYMBOL_STRATEGY_CONFIG      ← Tham số chiến lược riêng từng symbol
            │
            └── STRATEGY_VERSION    ← Lịch sử thay đổi tham số theo thời gian

RESEARCH_RUN                        ← Một phiên backtest/paper/live
    │
    ├── (FK) SYMBOL_STRATEGY_CONFIG ← Run này dùng config nào của symbol nào
    │
    ├── PERCENTILE_CACHE            ← Rolling percentile tại mỗi bar (chống look-ahead)
    ├── MARKET_REGIME_LOG           ← Trạng thái volatility regime theo giờ
    │
    ├── COMPRESSION_EVENT
    │       ├── FEATURE_SNAPSHOT    ← Raw feature values tại thời điểm detect
    │       ├── FILTER_LOG          ← Lý do reject ở stage COMPRESSION
    │       │
    │       └── BREAKOUT_EVENT
    │               ├── FILTER_LOG  ← Lý do reject ở stage BREAKOUT
    │               │
    │               └── EXPANSION_EVENT
    │                       ├── FILTER_LOG  ← Lý do reject ở stage EXPANSION
    │                       │
    │                       └── TRADE
    │                               ├── EXIT_EVENT  (nhiều dòng, mỗi lần thoát)
    │                               └── ORDER_LOG   (nhiều dòng, mỗi lệnh gửi sàn)
    │
    ├── CONTEXT_FILTER_LOG          ← Log EMA50 direction & volatility state filter
    ├── SESSION_STATE               ← Trạng thái risk engine, persist qua restart
    └── EQUITY_SNAPSHOT             ← Equity curve, tính drawdown

WALK_FORWARD_WINDOW                 ← Quản lý in-sample / out-of-sample windows
    └── (FK) RESEARCH_RUN x2       ← train_run + test_run
```

---

## NHÓM 1 — Quản lý Symbol (Symbol Registry)

---

### Bảng: SYMBOL_REGISTRY

Mục đích: Danh sách tất cả symbol mà hệ thống biết đến. Thêm symbol mới = thêm 1 dòng vào bảng này, không cần thay đổi code.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `symbol_id` | UUID | PK | Định danh nội bộ |
| `symbol` | VARCHAR(20) | UNIQUE NOT NULL | Tên cặp giao dịch. Ví dụ: BTCUSDC, SOLUSDC |
| `base_asset` | VARCHAR(10) | NOT NULL | Tài sản gốc. Ví dụ: BTC, SOL |
| `quote_asset` | VARCHAR(10) | NOT NULL | Tài sản định giá. Ví dụ: USDC, USDT |
| `exchange` | VARCHAR(20) | NOT NULL | Tên sàn. Ví dụ: BINANCE |
| `contract_type` | VARCHAR(10) | NOT NULL | Loại hợp đồng. Giá trị: PERP hoặc FUTURES |
| `is_active` | BOOLEAN | NOT NULL | Symbol có đang được giao dịch không |
| `is_in_universe` | BOOLEAN | NOT NULL | Symbol có nằm trong universe hiện tại không |
| `added_at` | TIMESTAMP | NOT NULL | Ngày bổ sung vào hệ thống |
| `deactivated_at` | TIMESTAMP | nullable | Ngày ngừng giao dịch nếu có |
| `notes` | TEXT | nullable | Ghi chú thủ công |

Lưu ý: Trường `is_in_universe` cho phép tắt/bật symbol khỏi universe mà không cần xóa dữ liệu lịch sử.

---

### Bảng: SYMBOL_EXCHANGE_CONFIG

Mục đích: Thông số kỹ thuật từ sàn giao dịch cho từng symbol. Tách khỏi tham số chiến lược vì đây là thông tin từ sàn, không phải do researcher quyết định.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `config_id` | UUID | PK | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `lot_size_step` | DECIMAL(18,8) | NOT NULL | Bước khối lượng tối thiểu |
| `min_qty` | DECIMAL(18,8) | NOT NULL | Số lượng tối thiểu của 1 lệnh |
| `max_qty` | DECIMAL(18,8) | nullable | Số lượng tối đa của 1 lệnh |
| `min_notional` | DECIMAL(18,2) | NOT NULL | Giá trị notional tối thiểu tính bằng USD |
| `price_tick_size` | DECIMAL(18,8) | NOT NULL | Bước giá tối thiểu |
| `maker_fee_pct` | DECIMAL(8,6) | NOT NULL | Phí maker tính theo phần trăm |
| `taker_fee_pct` | DECIMAL(8,6) | NOT NULL | Phí taker tính theo phần trăm |
| `default_leverage` | INTEGER | NOT NULL | Đòn bẩy mặc định |
| `max_leverage` | INTEGER | NOT NULL | Đòn bẩy tối đa sàn cho phép |
| `margin_type` | VARCHAR(10) | NOT NULL | Chế độ ký quỹ. Giá trị: ISOLATED hoặc CROSS |
| `effective_from` | TIMESTAMP | NOT NULL | Config này có hiệu lực từ khi nào |
| `effective_to` | TIMESTAMP | nullable | Config này hết hiệu lực khi nào. NULL = đang dùng |
| `source` | VARCHAR(20) | NOT NULL | Nguồn lấy config. Ví dụ: API_FETCH hoặc MANUAL |
| `fetched_at` | TIMESTAMP | NOT NULL | Thời điểm lấy config từ sàn |

Lưu ý: Thiết kế theo dạng lịch sử (effective_from / effective_to) để biết bot đang dùng config sàn nào tại mỗi thời điểm, phục vụ audit.

---

### Bảng: SYMBOL_STRATEGY_CONFIG

Mục đích: Bộ tham số chiến lược CBX riêng cho từng symbol. Đây là trái tim của kiến trúc per-symbol. Mỗi symbol có thể có ngưỡng ATR khác nhau, cửa sổ percentile khác nhau, điều kiện breakout khác nhau.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `strategy_config_id` | UUID | PK | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `version` | INTEGER | NOT NULL | Số phiên bản tăng dần. Bắt đầu từ 1 |
| `is_current` | BOOLEAN | NOT NULL | Đây có phải config đang dùng không |
| `created_at` | TIMESTAMP | NOT NULL | Ngày tạo config này |
| `created_by` | VARCHAR(50) | NOT NULL | Ai tạo. Giá trị: RESEARCHER hoặc OPTIMIZER hoặc WALKFORWARD |
| `based_on_version` | INTEGER | nullable | Kế thừa từ version nào, NULL nếu tạo mới |
| `change_reason` | TEXT | nullable | Lý do thay đổi so với version trước |
| **— Compression parameters —** | | | |
| `atr_period` | INTEGER | NOT NULL | Chu kỳ tính ATR. Mặc định: 14 |
| `atr_percentile_window` | INTEGER | NOT NULL | Cửa sổ rolling để tính percentile ATR. Mặc định: 120 |
| `atr_percentile_threshold` | DECIMAL(5,2) | NOT NULL | Ngưỡng percentile ATR để xác nhận compression. Mặc định: 20.0 |
| `range_bars` | INTEGER | NOT NULL | Số bar để tính rolling range. Mặc định: 12 |
| `range_percentile_threshold` | DECIMAL(5,2) | NOT NULL | Ngưỡng percentile range. Mặc định: 20.0 |
| `bb_period` | INTEGER | NOT NULL | Chu kỳ Bollinger Band. Mặc định: 20 |
| `bb_std` | DECIMAL(4,2) | NOT NULL | Số độ lệch chuẩn BB. Mặc định: 2.0 |
| `bb_width_percentile_threshold` | DECIMAL(5,2) | NOT NULL | Ngưỡng percentile BB width. Mặc định: 20.0 |
| `volume_percentile_threshold` | DECIMAL(5,2) | NOT NULL | Ngưỡng volume percentile tối đa trong vùng nén. Mặc định: 60.0 |
| `compression_min_bars` | INTEGER | NOT NULL | Số bar tối thiểu để xác nhận vùng nén. Mặc định: 8 |
| `compression_max_bars` | INTEGER | NOT NULL | Số bar tối đa của vùng nén. Mặc định: 24 |
| `min_conditions_met` | INTEGER | NOT NULL | Số điều kiện tối thiểu phải thỏa mãn trong 4 điều kiện. Mặc định: 3 |
| **— Breakout parameters —** | | | |
| `breakout_distance_min_atr` | DECIMAL(5,3) | NOT NULL | Khoảng cách phá vỡ tối thiểu tính theo ATR. Mặc định: 0.20 |
| `breakout_body_ratio_min` | DECIMAL(5,3) | NOT NULL | Tỷ lệ thân nến tối thiểu. Mặc định: 0.60 |
| `breakout_close_position_long` | DECIMAL(5,3) | NOT NULL | Close phải nằm trong top X% của nến LONG. Mặc định: 0.75 |
| `breakout_close_position_short` | DECIMAL(5,3) | NOT NULL | Close phải nằm trong bottom X% của nến SHORT. Mặc định: 0.25 |
| `breakout_volume_ratio_min` | DECIMAL(5,3) | NOT NULL | Volume tối thiểu so với SMA20. Mặc định: 1.30 |
| `breakout_volume_percentile_min` | DECIMAL(5,2) | NOT NULL | Hoặc volume percentile tối thiểu. Mặc định: 70.0 |
| `breakout_bar_size_max_atr` | DECIMAL(5,2) | NOT NULL | Kích thước bar tối đa tính theo ATR, lọc exhaustion. Mặc định: 2.50 |
| `false_break_limit` | INTEGER | NOT NULL | Số lần false break tối đa trong 10 bar gần nhất. Mặc định: 2 |
| **— Expansion parameters —** | | | |
| `expansion_lookforward_bars` | INTEGER | NOT NULL | Số bar chờ expansion confirmation. Mặc định: 3 |
| `expansion_body_loss_max_pct` | DECIMAL(5,2) | NOT NULL | Tỷ lệ body tối đa có thể mất để vẫn xác nhận. Mặc định: 50.0 |
| **— Entry parameters —** | | | |
| `retest_max_bars` | INTEGER | NOT NULL | Số bar chờ retest tối đa với RT entry. Mặc định: 3 |
| **— Stop loss parameters —** | | | |
| `stop_loss_atr_buffer` | DECIMAL(5,3) | NOT NULL | Khoảng cách stop loss tính theo ATR từ biên vùng nén. Mặc định: 0.25 |
| **— Exit parameters —** | | | |
| `partial_exit_r_level` | DECIMAL(5,2) | NOT NULL | Mức R để chốt lời một phần. Mặc định: 1.0 |
| `partial_exit_pct` | DECIMAL(5,2) | NOT NULL | Phần trăm vị thế chốt ở mức partial. Mặc định: 50.0 |
| `time_stop_bars` | INTEGER | NOT NULL | Số bar tối đa giữ lệnh trước khi time stop. Mặc định: 8 |
| **— Context filter parameters —** | | | |
| `ema_period_context` | INTEGER | NOT NULL | Chu kỳ EMA trên timeframe context. Mặc định: 50 |
| `context_timeframe` | VARCHAR(5) | NOT NULL | Timeframe context. Mặc định: 1h |
| `execution_timeframe` | VARCHAR(5) | NOT NULL | Timeframe thực thi. Mặc định: 15m |
| **— Risk parameters —** | | | |
| `risk_per_trade_pct` | DECIMAL(6,4) | NOT NULL | Phần trăm equity rủi ro mỗi lệnh. Mặc định: 0.25 |
| `max_position_per_symbol` | INTEGER | NOT NULL | Số vị thế tối đa trên symbol này cùng lúc. Mặc định: 1 |

---

### Bảng: STRATEGY_VERSION_HISTORY

Mục đích: Lưu lịch sử thay đổi tham số để biết parameter nào thay đổi giữa các version, phục vụ phân tích impact.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `history_id` | UUID | PK | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `from_version` | INTEGER | NOT NULL | Version cũ |
| `to_version` | INTEGER | NOT NULL | Version mới |
| `changed_at` | TIMESTAMP | NOT NULL | Thời điểm thay đổi |
| `changed_by` | VARCHAR(50) | NOT NULL | Ai thay đổi |
| `params_diff` | JSON | NOT NULL | Danh sách tham số thay đổi. Ví dụ: {"atr_percentile_threshold": {"from": 20, "to": 18}} |
| `reason` | TEXT | nullable | Lý do thay đổi |
| `backtest_result_before` | JSON | nullable | Kết quả backtest trước khi đổi |
| `backtest_result_after` | JSON | nullable | Kết quả backtest sau khi đổi |

---

## NHÓM 2 — Quản lý Phiên Chạy (Research Run)

---

### Bảng: RESEARCH_RUN

Mục đích: Mỗi backtest, paper trading, hoặc live trading là một run riêng biệt. Run luôn gắn với một symbol và một version config cụ thể.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `run_id` | UUID | PK | Định danh duy nhất |
| `run_name` | VARCHAR(100) | NOT NULL | Tên mô tả. Ví dụ: CBX_FT_BTC_2024Q1_v2 |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | Symbol của run này |
| `strategy_config_id` | UUID | FK → SYMBOL_STRATEGY_CONFIG | Config sử dụng |
| `mode` | VARCHAR(10) | NOT NULL | Chế độ chạy. Giá trị: BACKTEST hoặc PAPER hoặc LIVE |
| `status` | VARCHAR(10) | NOT NULL | Trạng thái. Giá trị: RUNNING hoặc COMPLETED hoặc FAILED hoặc ABORTED |
| `entry_model` | VARCHAR(20) | NOT NULL | Mô hình entry. Giá trị: FOLLOW_THROUGH hoặc RETEST hoặc BOTH |
| `side_filter` | VARCHAR(10) | NOT NULL | Chiều giao dịch. Giá trị: LONG_ONLY hoặc SHORT_ONLY hoặc BOTH |
| `data_start` | TIMESTAMP | NOT NULL | Dữ liệu bắt đầu từ khi nào |
| `data_end` | TIMESTAMP | NOT NULL | Dữ liệu kết thúc khi nào |
| `run_start` | TIMESTAMP | NOT NULL | Thời điểm bắt đầu chạy |
| `run_end` | TIMESTAMP | nullable | Thời điểm kết thúc. NULL nếu đang chạy |
| `git_commit` | VARCHAR(40) | NOT NULL | Hash code phiên bản code |
| `total_events_detected` | INTEGER | nullable | Tổng số compression event phát hiện |
| `total_breakouts` | INTEGER | nullable | Tổng số breakout event |
| `total_trades` | INTEGER | nullable | Tổng số trade kết thúc |
| `win_count` | INTEGER | nullable | Số trade thắng |
| `loss_count` | INTEGER | nullable | Số trade thua |
| `win_rate` | DECIMAL(6,4) | nullable | Tỷ lệ thắng |
| `total_pnl_r` | DECIMAL(10,4) | nullable | Tổng PnL tính theo R |
| `max_drawdown_r` | DECIMAL(10,4) | nullable | Max drawdown theo R |
| `sharpe_ratio` | DECIMAL(8,4) | nullable | Sharpe ratio |
| `profit_factor` | DECIMAL(8,4) | nullable | Profit factor |
| `notes` | TEXT | nullable | Ghi chú thủ công của researcher |

Lưu ý quan trọng: Mỗi run chỉ gắn với MỘT symbol. Để chạy backtest cho nhiều symbol cùng lúc, tạo nhiều run riêng rồi tổng hợp kết quả ở tầng reporting. Điều này đảm bảo mỗi run có thể audit độc lập.

---

## NHÓM 3 — Cache & Regime (Chống Look-ahead Bias)

---

### Bảng: PERCENTILE_CACHE

Mục đích: Lưu giá trị rolling percentile tại mỗi bar để đảm bảo không có look-ahead bias. Đây là bằng chứng audit quan trọng nhất của hệ thống.

Giải thích vấn đề: Nếu tính percentile trực tiếp trên toàn bộ dataset, bar số 100 sẽ biết thông tin của bar 500. Trong thực chiến, tại bar 100 ta chỉ có 100 bar trước đó. Bảng này lưu giá trị percentile đúng như bot đã thấy tại thời điểm đó.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `cache_id` | UUID | PK | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `bar_time` | TIMESTAMP | NOT NULL | Thời điểm bar |
| `timeframe` | VARCHAR(5) | NOT NULL | Ví dụ: 15m |
| `window_size` | INTEGER | NOT NULL | Kích thước cửa sổ rolling thực tế dùng để tính |
| `is_expanding` | BOOLEAN | NOT NULL | True nếu dùng expanding window vì chưa đủ data, False nếu dùng rolling chuẩn |
| `atr_normalized_value` | DECIMAL(12,8) | NOT NULL | Giá trị ATR/close tại bar này |
| `atr_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của ATR/close trong window |
| `range_value` | DECIMAL(12,8) | NOT NULL | Giá trị rolling range tại bar này |
| `range_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của range trong window |
| `bb_width_value` | DECIMAL(12,8) | NOT NULL | Giá trị BB width/close tại bar này |
| `bb_width_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của BB width trong window |
| `volume_value` | DECIMAL(20,2) | NOT NULL | Giá trị volume tại bar này |
| `volume_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của volume trong window |

Lưu ý: Đánh index kết hợp (run_id, symbol_id, bar_time) để query nhanh khi cần tra cứu giá trị percentile tại một thời điểm cụ thể.

---

### Bảng: MARKET_REGIME_LOG

Mục đích: Ghi nhận trạng thái volatility regime theo giờ. Phục vụ Context Filter 2 (Volatility State Guardrail) và phân tích sau này để biết chiến lược hoạt động tốt nhất ở regime nào.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `regime_id` | UUID | PK | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `bar_time` | TIMESTAMP | NOT NULL | Thời điểm bar 1h |
| `realized_vol_24h` | DECIMAL(10,6) | NOT NULL | Realized volatility 24 giờ |
| `realized_vol_1h` | DECIMAL(10,6) | NOT NULL | Realized volatility 1 giờ |
| `vol_percentile_90d` | DECIMAL(6,4) | NOT NULL | Percentile của realized vol so với 90 ngày gần nhất |
| `regime` | VARCHAR(15) | NOT NULL | Trạng thái regime. Giá trị: NORMAL hoặc LOW_VOL hoặc HIGH_VOL hoặc SHOCK |
| `regime_reason` | VARCHAR(100) | nullable | Lý do xác định regime |
| `is_tradeable` | BOOLEAN | NOT NULL | Filter 2 có cho phép giao dịch không |
| `block_reason` | VARCHAR(100) | nullable | Lý do block nếu is_tradeable = False |
| `ema50_1h` | DECIMAL(18,6) | NOT NULL | Giá trị EMA50 trên 1h |
| `ema50_slope` | DECIMAL(10,6) | NOT NULL | Độ dốc EMA50 (thay đổi trong N bar gần nhất / N) |
| `close_1h` | DECIMAL(18,6) | NOT NULL | Giá close của bar 1h |
| `close_vs_ema50_pct` | DECIMAL(8,4) | NOT NULL | Phần trăm chênh lệch giữa close và EMA50 |

Lưu ý: Regime SHOCK được xác định khi realized_vol_1h vượt quá ngưỡng cấu hình, thường là khi vol_percentile_90d >= 90. LOW_VOL khi vol_percentile_90d <= 10.

---

## NHÓM 4 — Sự Kiện (Event Study)

---

### Bảng: FEATURE_SNAPSHOT

Mục đích: Lưu toàn bộ raw feature values tại thời điểm compression được detect. Cho phép tái tính mọi quyết định mà không cần chạy lại toàn bộ pipeline.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `snapshot_id` | UUID | PK | |
| `event_id` | UUID | FK → COMPRESSION_EVENT | |
| `bar_time` | TIMESTAMP | NOT NULL | Thời điểm bar cuối của vùng nén |
| `close` | DECIMAL(18,6) | NOT NULL | Giá đóng cửa |
| `atr_14` | DECIMAL(18,6) | NOT NULL | Giá trị ATR(14) tuyệt đối |
| `atr_normalized` | DECIMAL(12,8) | NOT NULL | ATR(14) chia cho close |
| `atr_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của ATR_normalized, lấy từ PERCENTILE_CACHE |
| `range_12` | DECIMAL(12,8) | NOT NULL | (highest_high(12) - lowest_low(12)) chia cho close |
| `range_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của range_12, lấy từ PERCENTILE_CACHE |
| `bb_width` | DECIMAL(12,8) | NOT NULL | Bollinger Band width chia cho close |
| `bb_width_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của bb_width, lấy từ PERCENTILE_CACHE |
| `volume_sma20` | DECIMAL(20,2) | NOT NULL | SMA20 của volume |
| `volume_ratio` | DECIMAL(10,4) | NOT NULL | Volume hiện tại chia SMA20 |
| `volume_percentile` | DECIMAL(6,4) | NOT NULL | Percentile của volume, lấy từ PERCENTILE_CACHE |
| `ema50_1h` | DECIMAL(18,6) | NOT NULL | EMA50 trên timeframe 1h |
| `ema50_slope` | DECIMAL(10,6) | NOT NULL | Độ dốc EMA50 1h |
| `realized_vol_1h` | DECIMAL(10,6) | NOT NULL | Realized volatility trên 1h |
| `close_vs_ema50_pct` | DECIMAL(8,4) | NOT NULL | (close - EMA50) chia EMA50 nhân 100 |

---

### Bảng: COMPRESSION_EVENT

Mục đích: Ghi lại mọi vùng nén biến động được phát hiện.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `event_id` | UUID | PK | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `timeframe` | VARCHAR(5) | NOT NULL | Ví dụ: 15m |
| `start_time` | TIMESTAMP | NOT NULL | Bar đầu tiên của vùng nén |
| `end_time` | TIMESTAMP | NOT NULL | Bar cuối của vùng nén |
| `bar_count` | INTEGER | NOT NULL | Số bar kéo dài, phải trong khoảng 8 đến 24 |
| `high` | DECIMAL(18,6) | NOT NULL | Đỉnh vùng nén = compression_high |
| `low` | DECIMAL(18,6) | NOT NULL | Đáy vùng nén = compression_low |
| `width_pct` | DECIMAL(8,4) | NOT NULL | (high - low) chia close nhân 100 |
| `width_atr_ratio` | DECIMAL(8,4) | NOT NULL | (high - low) chia ATR, đo độ rộng vùng nén theo ATR |
| `atr_value` | DECIMAL(18,6) | NOT NULL | Giá trị ATR tuyệt đối tại thời điểm detect |
| `atr_percentile` | DECIMAL(6,4) | NOT NULL | |
| `range_percentile` | DECIMAL(6,4) | NOT NULL | |
| `bb_width_percentile` | DECIMAL(6,4) | NOT NULL | |
| `vol_percentile` | DECIMAL(6,4) | NOT NULL | |
| `conditions_met` | INTEGER | NOT NULL | Số điều kiện thỏa mãn, phải >= min_conditions_met trong config |
| `false_break_count` | INTEGER | NOT NULL | Số lần giá rò biên trong vùng nén trước breakout |
| `quality_score` | DECIMAL(6,4) | NOT NULL | Điểm chất lượng tổng hợp từ 0 đến 1 để rank event |
| `is_valid` | BOOLEAN | NOT NULL | Có đủ điều kiện để tiếp tục scan breakout không |
| `invalid_reason` | VARCHAR(200) | nullable | Lý do nếu is_valid = False |

---

### Bảng: BREAKOUT_EVENT

Mục đích: Ghi lại khi giá phá vỡ vùng nén.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `breakout_id` | UUID | PK | |
| `event_id` | UUID | FK → COMPRESSION_EVENT | |
| `time` | TIMESTAMP | NOT NULL | Thời điểm bar breakout đóng cửa |
| `side` | VARCHAR(5) | NOT NULL | Chiều breakout. Giá trị: LONG hoặc SHORT |
| `open` | DECIMAL(18,6) | NOT NULL | Giá mở cửa bar breakout |
| `high` | DECIMAL(18,6) | NOT NULL | Giá cao nhất bar breakout |
| `low` | DECIMAL(18,6) | NOT NULL | Giá thấp nhất bar breakout |
| `close` | DECIMAL(18,6) | NOT NULL | Giá đóng cửa bar breakout |
| `breakout_price_level` | DECIMAL(18,6) | NOT NULL | Ngưỡng bị phá. compression_high nếu LONG, compression_low nếu SHORT |
| `breakout_distance` | DECIMAL(18,6) | NOT NULL | Khoảng cách phá vỡ tuyệt đối |
| `breakout_distance_atr` | DECIMAL(8,4) | NOT NULL | breakout_distance chia ATR, phải >= breakout_distance_min_atr trong config |
| `bar_size_atr` | DECIMAL(8,4) | NOT NULL | Kích thước toàn bộ bar chia ATR, phải <= breakout_bar_size_max_atr |
| `body_to_range` | DECIMAL(6,4) | NOT NULL | Tỷ lệ thân nến, phải >= breakout_body_ratio_min |
| `close_position_in_candle` | DECIMAL(6,4) | NOT NULL | Vị trí close trong nến từ 0 đến 1, với 0 là low và 1 là high |
| `vol_ratio` | DECIMAL(8,4) | NOT NULL | Volume chia SMA20 |
| `vol_percentile` | DECIMAL(6,4) | NOT NULL | Percentile volume |
| `is_wick_dominant` | BOOLEAN | NOT NULL | Wick có chiếm ưu thế không |
| `is_valid` | BOOLEAN | NOT NULL | Breakout có hợp lệ không |
| `invalid_reason` | VARCHAR(200) | nullable | Lý do cụ thể nếu is_valid = False |

---

### Bảng: EXPANSION_EVENT

Mục đích: Xác nhận hoặc bác bỏ breakout dựa trên follow-through trong 1 đến 3 bar tiếp theo.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `expansion_id` | UUID | PK | |
| `breakout_id` | UUID | FK → BREAKOUT_EVENT | |
| `is_confirmed` | BOOLEAN | NOT NULL | Expansion được xác nhận không |
| `rejection_reason` | VARCHAR(200) | nullable | Lý do nếu is_confirmed = False |
| `confirmation_bar_index` | INTEGER | nullable | Xác nhận sau bao nhiêu bar, từ 1 đến 3 |
| `confirmation_time` | TIMESTAMP | nullable | Thời điểm xác nhận |
| `max_extension_atr` | DECIMAL(8,4) | nullable | Giá đi xa nhất tính theo ATR |
| `max_extension_price` | DECIMAL(18,6) | nullable | Giá tuyệt đối đi xa nhất |
| `reentry_occurred` | BOOLEAN | NOT NULL | Có quay lại vùng nén không |
| `reentry_depth_pct` | DECIMAL(8,4) | nullable | Độ sâu quay lại tính theo phần trăm width vùng nén |
| `body_loss_pct` | DECIMAL(8,4) | NOT NULL | Phần trăm body breakout candle đã mất |
| `higher_high_formed` | BOOLEAN | nullable | Với LONG: bar tiếp theo có tạo higher high không |
| `lower_low_formed` | BOOLEAN | nullable | Với SHORT: bar tiếp theo có tạo lower low không |

---

## NHÓM 5 — Vận Hành (Trades & Risk)

---

### Bảng: TRADE

Mục đích: Lưu kết quả tổng hợp của một giao dịch.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `trade_id` | UUID | PK | |
| `expansion_id` | UUID | FK → EXPANSION_EVENT | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `side` | VARCHAR(5) | NOT NULL | Chiều giao dịch. Giá trị: LONG hoặc SHORT |
| `entry_model` | VARCHAR(20) | NOT NULL | Mô hình entry. Giá trị: FOLLOW_THROUGH hoặc RETEST |
| `exit_model` | VARCHAR(20) | nullable | Mô hình exit thực tế. Giá trị: FIXED_R hoặc TIME_STOP hoặc STRUCTURE_FAIL hoặc TRAILING |
| `entry_time` | TIMESTAMP | NOT NULL | |
| `entry_price` | DECIMAL(18,6) | NOT NULL | |
| `stop_loss_price` | DECIMAL(18,6) | NOT NULL | Stop loss ban đầu |
| `initial_risk_r_price` | DECIMAL(18,6) | NOT NULL | Khoảng cách R = entry_price - stop_loss_price |
| `position_size` | DECIMAL(18,6) | NOT NULL | Khối lượng tính theo đơn vị hợp đồng |
| `position_size_usd` | DECIMAL(18,2) | NOT NULL | Giá trị notional tính bằng USD |
| `risk_amount_usd` | DECIMAL(18,2) | NOT NULL | Số USD rủi ro = equity tại thời điểm vào nhân risk_per_trade_pct |
| `exit_time` | TIMESTAMP | nullable | Thời điểm đóng hoàn toàn |
| `avg_exit_price` | DECIMAL(18,6) | nullable | Giá thoát trung bình có trọng số |
| `hold_bars` | INTEGER | nullable | Số bar giữ lệnh |
| `MFE_r` | DECIMAL(10,4) | nullable | Max Favorable Excursion tính theo R |
| `MAE_r` | DECIMAL(10,4) | nullable | Max Adverse Excursion tính theo R |
| `MFE_price` | DECIMAL(18,6) | nullable | Mức giá đạt MFE |
| `MAE_price` | DECIMAL(18,6) | nullable | Mức giá đạt MAE |
| `gross_pnl_usd` | DECIMAL(18,2) | nullable | PnL trước phí |
| `total_fees_usd` | DECIMAL(18,2) | nullable | Tổng phí entry cộng exit |
| `slippage_usd` | DECIMAL(18,2) | nullable | Slippage ước tính |
| `net_pnl_usd` | DECIMAL(18,2) | nullable | PnL sau phí và slippage |
| `total_pnl_r` | DECIMAL(10,4) | nullable | PnL tính theo R |
| `status` | VARCHAR(10) | NOT NULL | Trạng thái. Giá trị: OPEN hoặc CLOSED hoặc CANCELLED |
| `cancel_reason` | VARCHAR(200) | nullable | Lý do nếu CANCELLED, ví dụ: invalidation trước khi fill |

---

### Bảng: EXIT_EVENT

Mục đích: Theo dõi chi tiết từng lần thoát lệnh (partial hoặc full).

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `exit_id` | UUID | PK | |
| `trade_id` | UUID | FK → TRADE | |
| `exit_sequence` | INTEGER | NOT NULL | Thứ tự thoát. 1 là partial, 2 là final |
| `time` | TIMESTAMP | NOT NULL | |
| `exit_type` | VARCHAR(20) | NOT NULL | Loại thoát. Giá trị: PARTIAL_1R hoặc TRAILING hoặc STOP_LOSS hoặc TIME_STOP hoặc STRUCTURE_FAIL hoặc MANUAL |
| `trigger_price` | DECIMAL(18,6) | NOT NULL | Giá kích hoạt lệnh thoát |
| `fill_price` | DECIMAL(18,6) | NOT NULL | Giá thực tế được khớp |
| `size_closed` | DECIMAL(18,6) | NOT NULL | Khối lượng đóng lần này |
| `remaining_size` | DECIMAL(18,6) | NOT NULL | Còn bao nhiêu chưa đóng |
| `pnl_realized_r` | DECIMAL(10,4) | NOT NULL | PnL thực hiện tính theo R |
| `pnl_realized_usd` | DECIMAL(18,2) | NOT NULL | PnL USD lần này |
| `cumulative_pnl_r` | DECIMAL(10,4) | NOT NULL | PnL tích lũy tính đến exit này |
| `fee_usd` | DECIMAL(18,2) | NOT NULL | Phí của lần thoát này |
| `trailing_stop_level` | DECIMAL(18,6) | nullable | Mức trailing stop tại thời điểm exit |

---

### Bảng: ORDER_LOG

Mục đích: Ghi lại mọi lệnh gửi xuống sàn. Quan trọng cho live trading và paper trading để audit execution quality.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `order_id` | UUID | PK | ID nội bộ |
| `exchange_order_id` | VARCHAR(50) | nullable | ID trả về từ sàn |
| `trade_id` | UUID | FK → TRADE | |
| `time_sent` | TIMESTAMP | NOT NULL | Thời điểm gửi lệnh |
| `time_filled` | TIMESTAMP | nullable | Thời điểm được khớp |
| `order_type` | VARCHAR(15) | NOT NULL | Loại lệnh. Giá trị: MARKET hoặc LIMIT hoặc STOP_MARKET |
| `side` | VARCHAR(5) | NOT NULL | Giá trị: BUY hoặc SELL |
| `intent` | VARCHAR(15) | NOT NULL | Mục đích lệnh. Giá trị: ENTRY hoặc STOP_LOSS hoặc TAKE_PROFIT hoặc TRAILING_STOP |
| `requested_price` | DECIMAL(18,6) | nullable | Giá yêu cầu. NULL với MARKET order |
| `filled_price` | DECIMAL(18,6) | nullable | Giá khớp thực tế |
| `requested_qty` | DECIMAL(18,6) | NOT NULL | Khối lượng yêu cầu |
| `filled_qty` | DECIMAL(18,6) | nullable | Khối lượng khớp thực tế |
| `status` | VARCHAR(10) | NOT NULL | Giá trị: PENDING hoặc FILLED hoặc CANCELLED hoặc REJECTED |
| `reject_reason` | VARCHAR(200) | nullable | Lý do bị từ chối nếu có |
| `latency_ms` | INTEGER | nullable | Độ trễ từ gửi đến xác nhận tính bằng millisecond |

---

### Bảng: SESSION_STATE

Mục đích: Persist trạng thái Risk Engine qua các lần restart. Mỗi symbol có session state riêng.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `session_id` | UUID | PK | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `date` | DATE | NOT NULL | Ngày giao dịch |
| `equity_start_of_day` | DECIMAL(18,2) | NOT NULL | Equity đầu ngày tính bằng USD |
| `current_equity` | DECIMAL(18,2) | NOT NULL | Equity hiện tại |
| `current_daily_pnl_r` | DECIMAL(10,4) | NOT NULL | PnL ngày tính theo R |
| `current_daily_pnl_usd` | DECIMAL(18,2) | NOT NULL | PnL ngày tính USD |
| `consecutive_failures` | INTEGER | NOT NULL | Số breakout thất bại liên tiếp |
| `open_position_count` | INTEGER | NOT NULL | Số vị thế đang mở trên symbol này |
| `trading_halted` | BOOLEAN | NOT NULL | Bot có đang bị dừng không |
| `halt_reason` | VARCHAR(20) | nullable | Lý do dừng. Giá trị: DAILY_STOP hoặc CONSECUTIVE_FAIL hoặc MANUAL hoặc NULL |
| `halt_at` | TIMESTAMP | nullable | Thời điểm bị halt |
| `updated_at` | TIMESTAMP | NOT NULL | Lần cập nhật cuối |

---

### Bảng: EQUITY_SNAPSHOT

Mục đích: Lưu equity theo thời gian để vẽ equity curve và tính drawdown chính xác.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `snapshot_id` | UUID | PK | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `time` | TIMESTAMP | NOT NULL | Thời điểm snapshot |
| `trigger` | VARCHAR(15) | NOT NULL | Lý do ghi snapshot. Giá trị: TRADE_CLOSE hoặc DAILY_OPEN hoặc DAILY_CLOSE |
| `equity_usd` | DECIMAL(18,2) | NOT NULL | Tổng equity tại thời điểm này |
| `unrealized_pnl_usd` | DECIMAL(18,2) | NOT NULL | PnL chưa thực hiện |
| `realized_pnl_usd` | DECIMAL(18,2) | NOT NULL | PnL đã thực hiện cộng dồn từ đầu run |
| `drawdown_from_peak_pct` | DECIMAL(8,4) | NOT NULL | Drawdown so với đỉnh cao nhất tính theo phần trăm |
| `peak_equity` | DECIMAL(18,2) | NOT NULL | Đỉnh equity từ đầu run |
| `open_trades` | INTEGER | NOT NULL | Số lệnh đang mở |

---

## NHÓM 6 — Debug & Audit

---

### Bảng: FILTER_LOG

Mục đích: Ghi lại lý do bot từ chối một cơ hội tại từng stage. Là công cụ chính để debug và cải thiện chiến lược.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `log_id` | UUID | PK | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `event_id` | UUID | nullable, FK → COMPRESSION_EVENT | Điền nếu stage là COMPRESSION |
| `breakout_id` | UUID | nullable, FK → BREAKOUT_EVENT | Điền nếu stage là BREAKOUT |
| `expansion_id` | UUID | nullable, FK → EXPANSION_EVENT | Điền nếu stage là EXPANSION |
| `stage` | VARCHAR(15) | NOT NULL | Giai đoạn bị lọc. Giá trị: COMPRESSION hoặc BREAKOUT hoặc EXPANSION hoặc ENTRY |
| `filter_name` | VARCHAR(50) | NOT NULL | Tên filter. Ví dụ: ATR_PERCENTILE hoặc BODY_TO_RANGE hoặc WICK_DOMINANT hoặc BAR_TOO_LARGE hoặc VOL_TOO_LOW hoặc FALSE_BREAK_LIMIT |
| `value_at_time` | DECIMAL(12,6) | NOT NULL | Giá trị thực đo được |
| `threshold` | DECIMAL(12,6) | NOT NULL | Ngưỡng cần đạt |
| `decision` | VARCHAR(10) | NOT NULL | Giá trị: REJECTED hoặc PASSED |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `time` | TIMESTAMP | NOT NULL | |

---

### Bảng: CONTEXT_FILTER_LOG

Mục đích: Log riêng cho các filter bối cảnh 1h để phân tích impact của từng filter.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `log_id` | UUID | PK | |
| `run_id` | UUID | FK → RESEARCH_RUN | |
| `event_id` | UUID | FK → COMPRESSION_EVENT | |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `time` | TIMESTAMP | NOT NULL | |
| `filter_type` | VARCHAR(20) | NOT NULL | Giá trị: EMA50_DIRECTION hoặc VOLATILITY_STATE |
| `attempted_side` | VARCHAR(5) | NOT NULL | Chiều định giao dịch. Giá trị: LONG hoặc SHORT |
| `ema50_1h` | DECIMAL(18,6) | NOT NULL | |
| `close_1h` | DECIMAL(18,6) | NOT NULL | |
| `ema50_slope` | DECIMAL(10,6) | NOT NULL | |
| `vol_state` | VARCHAR(10) | NOT NULL | Giá trị: NORMAL hoặc LOW_VOL hoặc SHOCK |
| `realized_vol` | DECIMAL(10,6) | NOT NULL | |
| `decision` | VARCHAR(10) | NOT NULL | Giá trị: ALLOWED hoặc BLOCKED |
| `block_reason` | VARCHAR(200) | nullable | |

---

## NHÓM 7 — Walk-Forward Validation

---

### Bảng: WALK_FORWARD_WINDOW

Mục đích: Quản lý các cửa sổ in-sample và out-of-sample trong walk-forward validation. Mỗi symbol chạy walk-forward độc lập.

| Cột | Kiểu dữ liệu | Bắt buộc | Mô tả |
|-----|-------------|----------|-------|
| `window_id` | UUID | PK | |
| `wf_experiment_id` | UUID | NOT NULL | ID của toàn bộ experiment walk-forward, nhóm các window lại với nhau |
| `symbol_id` | UUID | FK → SYMBOL_REGISTRY | |
| `window_index` | INTEGER | NOT NULL | Số thứ tự window, bắt đầu từ 1 |
| `train_start` | TIMESTAMP | NOT NULL | |
| `train_end` | TIMESTAMP | NOT NULL | |
| `test_start` | TIMESTAMP | NOT NULL | |
| `test_end` | TIMESTAMP | NOT NULL | |
| `train_run_id` | UUID | FK → RESEARCH_RUN | Run in-sample |
| `test_run_id` | UUID | FK → RESEARCH_RUN | Run out-of-sample |
| `train_pnl_r` | DECIMAL(10,4) | nullable | Kết quả in-sample |
| `test_pnl_r` | DECIMAL(10,4) | nullable | Kết quả out-of-sample |
| `train_win_rate` | DECIMAL(6,4) | nullable | |
| `test_win_rate` | DECIMAL(6,4) | nullable | |
| `efficiency_ratio` | DECIMAL(8,4) | nullable | test_pnl chia train_pnl, đo mức độ overfit. Lý tưởng >= 0.5 |
| `best_params_json` | JSON | nullable | Tham số tối ưu từ giai đoạn train |
| `overfitting_flag` | BOOLEAN | nullable | True nếu efficiency_ratio < ngưỡng cảnh báo |

---

## Indexes khuyến nghị

```sql
-- Query thường xuyên nhất: tìm event theo symbol và thời gian
CREATE INDEX idx_compression_symbol_time ON COMPRESSION_EVENT(symbol_id, start_time);
CREATE INDEX idx_breakout_time_side ON BREAKOUT_EVENT(time, side);
CREATE INDEX idx_trade_symbol_time ON TRADE(symbol_id, entry_time, side);

-- Lọc theo run để phân tích từng experiment
CREATE INDEX idx_compression_run ON COMPRESSION_EVENT(run_id);
CREATE INDEX idx_trade_run ON TRADE(run_id);
CREATE INDEX idx_breakout_run ON BREAKOUT_EVENT(run_id);

-- Tra cứu percentile cache theo thời gian
CREATE UNIQUE INDEX idx_percentile_cache_lookup ON PERCENTILE_CACHE(run_id, symbol_id, bar_time, timeframe);

-- Regime lookup
CREATE INDEX idx_regime_symbol_time ON MARKET_REGIME_LOG(symbol_id, bar_time);

-- Debug filter performance
CREATE INDEX idx_filter_stage ON FILTER_LOG(run_id, stage, filter_name, decision);
CREATE INDEX idx_context_filter ON CONTEXT_FILTER_LOG(run_id, filter_type, decision);

-- Equity curve
CREATE INDEX idx_equity_run_time ON EQUITY_SNAPSHOT(run_id, time);

-- Strategy config lookup
CREATE INDEX idx_strategy_current ON SYMBOL_STRATEGY_CONFIG(symbol_id, is_current);
```

---

## Luồng ghi dữ liệu (Write Flow)

```
Symbol mới được thêm vào
    └── INSERT SYMBOL_REGISTRY
    └── INSERT SYMBOL_EXCHANGE_CONFIG   (lấy từ API sàn)
    └── INSERT SYMBOL_STRATEGY_CONFIG   (researcher cấu hình tham số)

Khởi động một Research Run
    └── INSERT RESEARCH_RUN             (gắn với symbol_id + strategy_config_id)

Bar 15m mới đến
    ├── [Percentile Engine]
    │       └── INSERT PERCENTILE_CACHE (is_expanding=True nếu < window_size bars)
    │
    ├── [Regime Engine] (chạy theo bar 1h, không phải 15m)
    │       └── INSERT MARKET_REGIME_LOG
    │
    ├── [Context Filter]
    │       └── INSERT CONTEXT_FILTER_LOG
    │
    ├── [Compression Detector]
    │       ├── Không đủ điều kiện
    │       │       └── INSERT FILTER_LOG (stage=COMPRESSION, decision=REJECTED)
    │       └── Đủ điều kiện
    │               ├── INSERT COMPRESSION_EVENT (is_valid=True)
    │               └── INSERT FEATURE_SNAPSHOT
    │                       │
    │                       └── [Breakout Detector]
    │                               ├── Không hợp lệ
    │                               │       ├── INSERT BREAKOUT_EVENT (is_valid=False)
    │                               │       └── INSERT FILTER_LOG (stage=BREAKOUT)
    │                               └── Hợp lệ
    │                                       ├── INSERT BREAKOUT_EVENT (is_valid=True)
    │                                       │
    │                                       └── [Expansion Validator] (chờ 1-3 bar)
    │                                               ├── Rejected
    │                                               │       ├── INSERT EXPANSION_EVENT (is_confirmed=False)
    │                                               │       └── INSERT FILTER_LOG (stage=EXPANSION)
    │                                               └── Confirmed
    │                                                       ├── INSERT EXPANSION_EVENT (is_confirmed=True)
    │                                                       │
    │                                                       └── [Entry Engine]
    │                                                               ├── Cancelled
    │                                                               │       └── INSERT TRADE (status=CANCELLED)
    │                                                               └── Filled
    │                                                                       ├── INSERT TRADE (status=OPEN)
    │                                                                       ├── INSERT ORDER_LOG (intent=ENTRY)
    │                                                                       └── UPDATE SESSION_STATE

Trade đang mở, mỗi bar
    └── Theo dõi MFE, MAE, trailing stop level

Trade đóng (partial hoặc full)
    ├── INSERT EXIT_EVENT
    ├── INSERT ORDER_LOG (intent=STOP_LOSS / TAKE_PROFIT / TRAILING_STOP)
    ├── UPDATE TRADE (nếu CLOSED: điền exit_time, avg_exit_price, pnl...)
    ├── UPDATE SESSION_STATE
    └── INSERT EQUITY_SNAPSHOT (trigger=TRADE_CLOSE)

Thêm symbol mới vào universe (mở rộng)
    ├── UPDATE SYMBOL_REGISTRY (is_in_universe=True)
    ├── INSERT SYMBOL_EXCHANGE_CONFIG  (config sàn mới nhất)
    └── INSERT SYMBOL_STRATEGY_CONFIG  (version=1, tham số mới)
        └── Researcher chạy backtest riêng cho symbol mới
            └── INSERT RESEARCH_RUN (symbol_id mới)
```

---

## Cơ chế mở rộng Symbol

Để thêm một symbol mới vào hệ thống (ví dụ: ETHUSDC), thực hiện các bước sau theo thứ tự:

Bước 1: Đăng ký symbol
```
INSERT SYMBOL_REGISTRY với is_active=True, is_in_universe=False
INSERT SYMBOL_EXCHANGE_CONFIG bằng cách fetch từ API sàn
```

Bước 2: Thiết kế tham số riêng cho symbol
```
INSERT SYMBOL_STRATEGY_CONFIG với version=1, is_current=True
Tham số có thể copy từ symbol tương tự rồi điều chỉnh
Ghi rõ created_by=RESEARCHER và change_reason
```

Bước 3: Chạy backtest riêng
```
INSERT RESEARCH_RUN với symbol_id mới
Chạy LONG_ONLY và SHORT_ONLY riêng biệt
Chạy FOLLOW_THROUGH và RETEST riêng biệt
```

Bước 4: Kích hoạt
```
UPDATE SYMBOL_REGISTRY SET is_in_universe=True
UPDATE SESSION_STATE (khởi tạo session mới cho symbol)
```

Không cần thay đổi code hay schema khi thêm symbol mới.

---

## Technology Stack gợi ý

| Thành phần | Lựa chọn | Lý do |
|------------|----------|-------|
| Database chính | PostgreSQL | Hỗ trợ UUID, JSON, query phức tạp |
| ORM | SQLAlchemy (Python) | Type-safe, dễ migrate |
| Migration | Alembic | Versioned schema changes |
| Time-series tăng tốc | TimescaleDB extension | Query theo time range nhanh hơn |
| Backtest in-memory | DuckDB | Query nhanh trên file parquet khi nghiên cứu |
| Session state cache | Redis | Persist SESSION_STATE tốc độ cao |
| Schema validation | Pydantic v2 | Đảm bảo data integrity trước khi INSERT |
