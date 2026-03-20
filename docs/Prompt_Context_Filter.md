Tạo Context Filter cho CBX Bot.

File: backend/app/strategy/context_filter.py

━━━ MỤC ĐÍCH ━━━
2 filter nhẹ để tránh giao dịch ngược hoàn toàn với bối cảnh
và tránh 2 trạng thái thái cực của volatility.
Không phải trend engine — chỉ là guardrail tối thiểu.

━━━ INPUT ━━━
- df_1h: DataFrame với ít nhất các cột:
    close, ema50 (đã tính bởi FeatureEngine),
    ema50_slope, realized_vol_1h
- attempted_side: Literal["LONG", "SHORT"]
- compression_zone: CompressionZone (để lấy atr_value)
- config: SymbolStrategyConfig

━━━ FILTER 1 — EMA50 Direction ━━━
Mục đích: Không trade ngược hoàn toàn với EMA50 1h.

LONG chỉ được phép khi:
  close_1h >= ema50_1h
  VÀ ema50_slope >= -slope_threshold
  (slope_threshold = 0.0003, đọc từ config nếu có, không hardcode)

SHORT chỉ được phép khi:
  close_1h <= ema50_1h
  VÀ ema50_slope <= +slope_threshold

Logic: Chỉ chặn khi CẢ HAI điều kiện fail.
Nếu chỉ fail 1 trong 2 → vẫn cho phép (filter nhẹ, không quá chặt).

Nói cách khác:
  LONG bị block nếu: close < ema50 VÀ slope âm mạnh
  SHORT bị block nếu: close > ema50 VÀ slope dương mạnh

━━━ FILTER 2 — Volatility State ━━━
Mục đích: Tránh 2 đầu thái cực của volatility.

Tính vol_percentile_90d:
  Percentile của realized_vol_1h trong rolling 90 ngày × 24 bars
  (= 2160 bars 1h gần nhất)

Xác định regime:
  SHOCK:    vol_percentile_90d >= 90  → BLOCKED
            Lý do: Breakout event mất ý nghĩa thống kê trong shock regime
  HIGH_VOL: 70 <= vol_percentile_90d < 90 → ALLOWED (cảnh báo nhưng cho phép)
  NORMAL:   10 < vol_percentile_90d < 70  → ALLOWED
  LOW_VOL:  vol_percentile_90d <= 10 → BLOCKED chỉ khi:
            breakout_distance_atr < 0.15
            (breakout quá nhỏ trong môi trường vol thấp = nhiễu)
            Ngược lại vẫn ALLOWED

━━━ OUTPUT: ContextFilterResult dataclass ━━━
- allowed: bool
- block_reason: Optional[str]
- filter_type: Optional[str]      ← "EMA50_DIRECTION" hoặc "VOLATILITY_STATE"
- attempted_side: str
- ema50_1h: Decimal
- close_1h: Decimal
- ema50_slope: Decimal
- vol_state: str                  ← "NORMAL", "LOW_VOL", "HIGH_VOL", "SHOCK"
- vol_percentile_90d: Decimal
- realized_vol_1h: Decimal
- close_vs_ema50_pct: Decimal     ← (close - ema50) / ema50 × 100

━━━ METHODS ━━━

Method chính:
  check(df_1h, attempted_side, compression_zone, config) -> ContextFilterResult

Method ghi DB:
  save_log(result, event_id, run_id, db_session) -> ContextFilterLog
  Ghi vào bảng CONTEXT_FILTER_LOG

Method phụ:
  get_current_regime(df_1h) -> str
  Trả về vol_state hiện tại, dùng trong Scanner để ghi MARKET_REGIME_LOG

━━━ TEST FILE ━━━
File: backend/tests/test_context_filter.py

8 test cases:

Test 1: LONG allowed — Normal regime, close > EMA50, slope flat
  → allowed=True, vol_state="NORMAL"

Test 2: LONG blocked — EMA50 filter
  close < ema50 VÀ slope âm mạnh (-0.001)
  → allowed=False, filter_type="EMA50_DIRECTION", block_reason chứa "LONG"

Test 3: SHORT allowed — Normal regime, close < EMA50, slope flat
  → allowed=True, vol_state="NORMAL"

Test 4: SHORT blocked — EMA50 filter
  close > ema50 VÀ slope dương mạnh (+0.001)
  → allowed=False, filter_type="EMA50_DIRECTION"

Test 5: BOTH blocked — SHOCK regime
  vol_percentile_90d = 95
  → allowed=False, filter_type="VOLATILITY_STATE", vol_state="SHOCK"

Test 6: LOW_VOL blocked — breakout quá nhỏ
  vol_percentile_90d = 5, breakout_distance_atr = 0.10 (< 0.15)
  → allowed=False, filter_type="VOLATILITY_STATE", vol_state="LOW_VOL"

Test 7: LOW_VOL allowed — breakout đủ lớn
  vol_percentile_90d = 5, breakout_distance_atr = 0.25 (>= 0.15)
  → allowed=True, vol_state="LOW_VOL"
  (LOW_VOL không chặn nếu breakout đủ mạnh)

Test 8: HIGH_VOL allowed — cảnh báo nhưng không block
  vol_percentile_90d = 75
  → allowed=True, vol_state="HIGH_VOL"

Chạy: python -m pytest backend/tests/test_context_filter.py -v
Expected: 8/8 PASSED

━━━ LƯU Ý QUAN TRỌNG ━━━
- KHÔNG dùng CCXT. Data 1h được truyền vào từ ngoài (df_1h parameter).
- Context Filter KHÔNG tự fetch data — chỉ nhận DataFrame và tính toán.
- Việc fetch df_1h là trách nhiệm của Scanner Loop ở bước sau.