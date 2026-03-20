Tạo Expansion Validator cho CBX Bot.

File: backend/app/strategy/expansion_validator.py

━━━ MỤC ĐÍCH ━━━
Sau khi BreakoutDetector xác nhận breakout hợp lệ, cần chờ 1-3 bar tiếp theo
để xác nhận giá thực sự đi theo chiều breakout — tránh false breakout.

━━━ INPUT ━━━
- breakout: BreakoutResult (is_valid=True)
- next_bars: List[dict] — tối đa 3 bar tiếp theo sau breakout bar
  mỗi bar là dict: {open_time, open, high, low, close, volume} với Decimal values
- zone: CompressionZone
- config: SymbolStrategyConfig

━━━ ĐIỀU KIỆN XÁC NHẬN LONG ━━━
Confirmed nếu thỏa ÍT NHẤT 1 trong 2 điều kiện:

Condition A — Higher High:
  bar tiếp theo tạo high > breakout_bar.high (higher high)
  VÀ close của bar đó > breakout.breakout_price_level (không close lại trong zone)

Condition B — Hold Above:
  Trong 2 bar tiếp theo, giá giữ trên breakout_price_level
  VÀ body_loss_pct < config.expansion_body_loss_max_pct (default 50%)
  body_loss_pct = (breakout_bar.close - current_low) / breakout_body_size × 100

━━━ ĐIỀU KIỆN XÁC NHẬN SHORT ━━━
Đối xứng với LONG:

Condition A — Lower Low:
  bar tiếp theo tạo low < breakout_bar.low (lower low)
  VÀ close < breakout.breakout_price_level (không close lại trong zone)

Condition B — Hold Below:
  Trong 2 bar tiếp theo, giá giữ dưới breakout_price_level
  VÀ body_loss_pct < config.expansion_body_loss_max_pct (default 50%)
  body_loss_pct = (current_high - breakout_bar.close) / breakout_body_size × 100

━━━ ĐIỀU KIỆN REJECTED ━━━
is_confirmed = False nếu bất kỳ điều nào xảy ra trong 3 bar:

1. REENTRY_DEEP:
   LONG: có bar close < breakout.breakout_price_level (đóng lại trong zone)
   SHORT: có bar close > breakout.breakout_price_level

2. BODY_LOSS_EXCEEDED:
   body_loss_pct >= config.expansion_body_loss_max_pct (default 50%)
   Tức là mất hơn 50% thân nến breakout theo chiều bất lợi

3. NO_FOLLOWTHROUGH:
   Sau đủ expansion_lookforward_bars (default 3) mà không có
   Condition A cũng không có Condition B nào thỏa → timeout

━━━ TÍNH THÊM ━━━
Trong quá trình validate, tính thêm:
- max_extension_price: giá đi xa nhất theo chiều breakout trong 3 bar
- max_extension_atr: (max_extension_price - breakout_price_level) / atr_value
- reentry_occurred: bool — có quay lại zone không
- reentry_depth_pct: nếu có reentry, sâu bao nhiêu % so với zone width

━━━ OUTPUT: ExpansionResult dataclass ━━━
- is_confirmed: bool
- rejection_reasons: List[str]    ← collect tất cả lý do fail
- confirmation_bar_index: Optional[int]  ← xác nhận ở bar thứ mấy (1, 2, hoặc 3)
- confirmed_by: Optional[str]     ← "CONDITION_A" hoặc "CONDITION_B"
- confirmation_time: Optional[datetime]
- max_extension_price: Decimal
- max_extension_atr: Decimal
- reentry_occurred: bool
- reentry_depth_pct: Decimal
- body_loss_pct: Decimal          ← max body loss trong 3 bar
- higher_high_formed: Optional[bool]   ← LONG only
- lower_low_formed: Optional[bool]     ← SHORT only

━━━ METHODS ━━━

Method chính:
  validate(breakout, next_bars, zone, config) -> ExpansionResult

  Logic xử lý next_bars:
  - Loop qua từng bar (tối đa 3)
  - Mỗi bar: check rejected conditions TRƯỚC (nếu có → dừng ngay)
  - Sau đó check confirmed conditions
  - Nếu confirmed → set confirmation_bar_index và break
  - Sau khi hết bars mà chưa confirmed → NO_FOLLOWTHROUGH

Method ghi DB:
  save_event(result, breakout_id, run_id, db_session) -> ExpansionEvent

Method ghi Filter Log:
  save_filter_logs(result, breakout_id, run_id, db_session)
  Ghi vào FILTER_LOG với stage="EXPANSION"

━━━ TEST FILE ━━━
File: backend/tests/test_expansion_validator.py

9 test cases:

Test 1: LONG confirmed — Condition A
  Bar+1: high > breakout_bar.high, close > compression_high
  → is_confirmed=True, confirmed_by="CONDITION_A", confirmation_bar_index=1

Test 2: LONG confirmed — Condition B (bar thứ 2)
  Bar+1: không thỏa A, giá hold trên compression_high
  Bar+2: vẫn hold, body_loss_pct=30%
  → is_confirmed=True, confirmed_by="CONDITION_B", confirmation_bar_index=2

Test 3: LONG rejected — REENTRY_DEEP
  Bar+1: close < compression_high (đóng lại trong zone)
  → is_confirmed=False, "REENTRY_DEEP" trong rejection_reasons

Test 4: LONG rejected — BODY_LOSS_EXCEEDED
  Bar+1: low xuống thấp làm body_loss_pct=65%
  → is_confirmed=False, "BODY_LOSS_EXCEEDED"

Test 5: LONG rejected — NO_FOLLOWTHROUGH
  Cả 3 bars: không tạo HH, không giữ trên level, nhưng cũng chưa reentry
  → is_confirmed=False, "NO_FOLLOWTHROUGH"

Test 6: SHORT confirmed — Condition A
  Bar+1: low < breakout_bar.low, close < compression_low
  → is_confirmed=True, confirmed_by="CONDITION_A", confirmation_bar_index=1

Test 7: SHORT confirmed — Condition B
  Tương tự Test 2 nhưng SHORT

Test 8: SHORT rejected — REENTRY_DEEP
  Bar+1: close > compression_low
  → is_confirmed=False, "REENTRY_DEEP"

Test 9: max_extension_atr tính đúng
  LONG confirmed, breakout_price_level=50000, max high trong 3 bar=50300, ATR=200
  → max_extension_atr = (50300-50000)/200 = 1.5
  Assert max_extension_atr == Decimal("1.5")

Chạy: python -m pytest backend/tests/test_expansion_validator.py -v
Expected: 9/9 PASSED