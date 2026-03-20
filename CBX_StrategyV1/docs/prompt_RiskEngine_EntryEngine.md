Tạo Risk Engine và Entry Engine cho CBX Bot.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 1: backend/app/strategy/risk_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class RiskEngine:

─── Method 1: check_can_trade() ───
Signature:
  async def check_can_trade(
      symbol_id: UUID,
      side: str,
      db: AsyncSession
  ) -> RiskCheckResult

Kiểm tra theo thứ tự SAU (dừng ngay khi gặp block đầu tiên):
  1. Load SessionState của symbol từ DB
  2. trading_halted == True → BLOCKED, reason="TRADING_HALTED"
  3. current_daily_pnl_r <= RISK_DAILY_STOP_R → BLOCKED,
     UPDATE trading_halted=True, halt_reason="DAILY_STOP"
  4. consecutive_failures >= RISK_CONSECUTIVE_FAIL_STOP → BLOCKED,
     UPDATE trading_halted=True, halt_reason="CONSECUTIVE_FAIL"
  5. open_position_count >= max_position_per_symbol → BLOCKED,
     reason="MAX_POSITION_SYMBOL"
  6. Query tổng open_position_count tất cả symbols của run này
     >= RISK_MAX_POSITIONS_PORTFOLIO → BLOCKED,
     reason="MAX_POSITION_PORTFOLIO"
  7. Tất cả pass → ALLOWED

RiskCheckResult dataclass:
  allowed: bool
  block_reason: Optional[str]
  current_daily_pnl_r: Decimal
  consecutive_failures: int
  open_position_count: int
  portfolio_position_count: int

─── Method 2: calculate_position_size() ───
Signature:
  def calculate_position_size(
      entry_price: Decimal,
      stop_price: Decimal,
      equity_usd: Decimal,
      config: SymbolStrategyConfig,
      exchange_config: SymbolExchangeConfig
  ) -> PositionSizeResult

Logic:
  risk_amount_usd = equity_usd × config.risk_per_trade_pct
  price_distance  = abs(entry_price - stop_price)
  raw_qty         = risk_amount_usd / price_distance

  Làm tròn XUỐNG theo lot_size_step:
    rounded_qty = floor(raw_qty / lot_size_step) × lot_size_step

  Kiểm tra min_qty:
    if rounded_qty < exchange_config.min_qty → qty = Decimal("0"), valid=False
  
  Kiểm tra min_notional:
    notional = rounded_qty × entry_price
    if notional < exchange_config.min_notional → valid=False

PositionSizeResult dataclass:
  qty: Decimal
  valid: bool
  invalid_reason: Optional[str]
  risk_amount_usd: Decimal
  notional_usd: Decimal
  price_distance: Decimal
  raw_qty: Decimal

─── Method 3: calculate_stop_loss() ───
Signature:
  def calculate_stop_loss(
      side: str,
      zone: CompressionZone,
      breakout_bar: dict,
      config: SymbolStrategyConfig
  ) -> Decimal

Logic:
  atr_buffer = zone.atr_value × config.stop_loss_atr_buffer

  LONG:
    level_1 = zone.high - atr_buffer
    level_2 = Decimal(str(breakout_bar["low"]))
    stop    = min(level_1, level_2)   ← lấy mức thấp hơn

  SHORT:
    level_1 = zone.low + atr_buffer
    level_2 = Decimal(str(breakout_bar["high"]))
    stop    = max(level_1, level_2)   ← lấy mức cao hơn

─── Method 4: update_session_on_open() ───
  async def update_session_on_open(symbol_id, run_id, db) -> SessionState
  Tăng open_position_count += 1
  Ghi EQUITY_SNAPSHOT với trigger="TRADE_OPEN"

─── Method 5: update_session_on_close() ───
  async def update_session_on_close(
      symbol_id, run_id, pnl_r: Decimal,
      trade_result: str, db
  ) -> SessionState
  Giảm open_position_count -= 1
  current_daily_pnl_r += pnl_r
  
  Nếu trade_result == "FAILED_BREAKOUT":
    consecutive_failures += 1
  Ngược lại:
    consecutive_failures = 0   ← reset khi có trade không phải failed breakout

  Ghi EQUITY_SNAPSHOT với trigger="TRADE_CLOSE"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 2: backend/app/strategy/entry_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class EntryEngine:
Nhận vào ExpansionResult đã confirmed và chuẩn bị entry order.
KHÔNG tự gọi Binance API — chỉ tính toán và trả về EntryOrder.
Việc thực thi lệnh là của OrderExecutor ở bước sau.

─── Entry Model FT (Follow-Through) ───
Vào lệnh ngay sau khi expansion confirmed:
  entry_price_estimate = open của bar kế tiếp sau confirmation bar
  Vì không biết open tương lai → estimate = close của confirmation bar
  Trong live: đặt MARKET order tại open bar tiếp theo

─── Entry Model RT (Retest) ───
Chờ giá quay lại test vùng breakout:
  LONG: chờ giá pullback về compression_high ± small_buffer
  SHORT: chờ giá pullback về compression_low ± small_buffer
  small_buffer = zone.atr_value × 0.05
  Timeout: config.retest_max_bars (default 3) bars sau confirmation
  Nếu hết timeout mà chưa retest → entry_order.is_valid = False

─── Method: prepare_entry() ───
Signature:
  def prepare_entry(
      expansion: ExpansionResult,
      breakout: BreakoutResult,
      zone: CompressionZone,
      entry_model: str,
      config: SymbolStrategyConfig
  ) -> EntryOrder

EntryOrder dataclass:
  is_valid: bool
  invalid_reason: Optional[str]
  symbol: str
  side: str                        ← từ breakout.side
  entry_model: str                 ← "FOLLOW_THROUGH" hoặc "RETEST"
  entry_price_estimate: Decimal
  stop_loss_price: Decimal         ← từ RiskEngine.calculate_stop_loss()
  tp1_price: Decimal               ← entry + 1R (LONG) hoặc entry - 1R (SHORT)
  initial_r_distance: Decimal      ← abs(entry - stop)
  zone_ref: CompressionZone        ← để Trade Manager dùng sau
  breakout_bar: dict               ← OHLCV của nến breakout

─── Method: is_still_valid() ───
Signature:
  def is_still_valid(
      entry_order: EntryOrder,
      current_bar: dict
  ) -> bool

Kiểm tra trước khi thực sự đặt lệnh:
  LONG: current_bar.close > zone.low (chưa invalidate)
        VÀ current_bar.close không quá xa entry_estimate (< 1.5 ATR)
  SHORT: ngược lại
  Nếu False → log "ENTRY_INVALIDATED_BEFORE_FILL"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File 1: backend/tests/test_risk_engine.py (7 cases)

Test 1: Position size đúng
  equity=10000, risk_pct=0.0025, entry=50000, stop=49900
  price_distance = 100
  risk_amount = 10000 × 0.0025 = 25 USDC
  raw_qty = 25 / 100 = 0.25
  lot_size_step=0.001 → rounded_qty=0.25
  Assert: qty==Decimal("0.25"), risk_amount_usd==Decimal("25")

Test 2: Position size làm tròn đúng
  raw_qty = 0.2567, lot_size_step = 0.001
  Assert: qty == Decimal("0.256")   ← floor, không round

Test 3: Position size dưới min_qty → invalid
  rounded_qty = 0.0005, min_qty = 0.001
  Assert: valid==False, reason contains "MIN_QTY"

Test 4: check_can_trade — daily stop hit
  Mock SessionState: current_daily_pnl_r = Decimal("-2.1")
  Assert: allowed==False, block_reason=="DAILY_STOP"

Test 5: check_can_trade — consecutive fail
  Mock SessionState: consecutive_failures = 3
  Assert: allowed==False, block_reason=="CONSECUTIVE_FAIL"

Test 6: check_can_trade — max position symbol
  Mock SessionState: open_position_count = 1, max_position_per_symbol = 1
  Assert: allowed==False, block_reason=="MAX_POSITION_SYMBOL"

Test 7: calculate_stop_loss LONG
  zone.high=50000, zone.atr_value=200, stop_loss_atr_buffer=0.25
  breakout_bar.low = 49950
  level_1 = 50000 - (200×0.25) = 49950
  level_2 = 49950
  stop = min(49950, 49950) = 49950
  Assert: stop == Decimal("49950")

File 2: backend/tests/test_entry_engine.py (4 cases)

Test 1: FT entry valid
  Expansion confirmed, side=LONG
  → is_valid=True, entry_model="FOLLOW_THROUGH"
  → tp1_price = entry + initial_r_distance

Test 2: RT entry valid — retest xảy ra
  Mock current bar: giá về đúng compression_high ± buffer
  → is_valid=True, entry_model="RETEST"

Test 3: RT entry invalid — timeout
  3 bars trôi qua không có retest
  → is_valid=False, reason="RETEST_TIMEOUT"

Test 4: is_still_valid False — giá đã đi quá xa
  current close cách entry_estimate > 1.5 ATR
  → is_still_valid returns False

Chạy:
  python -m pytest backend/tests/test_risk_engine.py -v
  python -m pytest backend/tests/test_entry_engine.py -v
Expected: 7/7 + 4/4 = 11 PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ SAFETY CHECKLIST — ĐỌC TRƯỚC KHI CHẠY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. BINANCE_TESTNET=true trong .env — bắt buộc
2. Risk Engine KHÔNG tự đặt lệnh — chỉ tính toán
3. Entry Engine KHÔNG gọi Binance API — chỉ chuẩn bị EntryOrder
4. Mọi lệnh thật chỉ xảy ra ở OrderExecutor (bước sau)
5. Test với equity giả: EQUITY_USD=1000 trong mock
6. Verify Test 1: risk_amount = 1000 × 0.0025 = 2.5 USDC
   qty = 2.5 / price_distance → phải rất nhỏ với BTC