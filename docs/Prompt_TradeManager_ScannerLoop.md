Tạo Trade Manager và Scanner Loop cho CBX Bot.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 1: backend/app/strategy/trade_manager.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class TradeManager:
Quản lý vòng đời của một Trade đang OPEN từ lúc vào đến lúc thoát.
KHÔNG gọi Binance API trực tiếp — trả về TradeAction để Scanner thực thi.

─── TradeAction dataclass ───
  action_type: str    ← "HOLD", "CLOSE_PARTIAL", "CLOSE_FULL"
  exit_type: Optional[str]
      Các giá trị: "STOP_LOSS", "PARTIAL_1R", "TRAILING",
                   "TIME_STOP", "STRUCTURE_FAIL"
  close_price: Optional[Decimal]   ← giá nên thoát
  size_to_close: Optional[Decimal] ← bao nhiêu qty đóng
  reason: str

─── Method chính: update() ───
Signature:
  def update(
      trade: Trade,
      current_bar: dict,
      zone: CompressionZone,
      config: SymbolStrategyConfig
  ) -> TradeAction

Kiểm tra theo thứ tự PRIORITY — dừng ngay khi tìm thấy action:

PRIORITY 1 — STOP_LOSS (kiểm tra đầu tiên, bảo vệ vốn):
  LONG: current_bar.low <= trade.stop_loss_price
        → TradeAction(CLOSE_FULL, "STOP_LOSS", trade.stop_loss_price)
  SHORT: current_bar.high >= trade.stop_loss_price
        → TradeAction(CLOSE_FULL, "STOP_LOSS", trade.stop_loss_price)

PRIORITY 2 — STRUCTURE_FAIL:
  LONG: current_bar.close < zone.low
        (đóng dưới đáy zone, không chỉ dưới compression_high)
  SHORT: current_bar.close > zone.high
        → TradeAction(CLOSE_FULL, "STRUCTURE_FAIL", current_bar.close)

PRIORITY 3 — TIME_STOP:
  trade.hold_bars >= config.time_stop_bars (default 8)
  VÀ chưa đạt 1R (total_pnl_r < config.partial_exit_r_level)
  → TradeAction(CLOSE_FULL, "TIME_STOP", current_bar.close)

PRIORITY 4 — PARTIAL_1R (chỉ thực hiện 1 lần):
  Điều kiện: trade.partial_exit_done == False
  LONG: current_bar.high >= trade.tp1_price
  SHORT: current_bar.low <= trade.tp1_price
  → TradeAction(CLOSE_PARTIAL, "PARTIAL_1R", trade.tp1_price,
                size=trade.position_size × config.partial_exit_pct)
  Sau khi execute: set trade.partial_exit_done = True

PRIORITY 5 — TRAILING (chỉ sau khi đã partial):
  Điều kiện: trade.partial_exit_done == True
  Trailing stop = 2-bar low/high:
    LONG: trailing_stop = min(bar[-1].low, bar[-2].low)
    SHORT: trailing_stop = max(bar[-1].high, bar[-2].high)
  Nếu LONG: current_bar.low <= trailing_stop
  → TradeAction(CLOSE_FULL, "TRAILING", trailing_stop)

DEFAULT — HOLD:
  Không có điều kiện nào triggered
  Update MFE/MAE, tăng hold_bars
  → TradeAction("HOLD", reason="No exit condition met")

─── Method: update_mfe_mae() ───
  def update_mfe_mae(trade: Trade, current_bar: dict) -> None
  
  LONG:
    favorable_price = current_bar.high
    adverse_price   = current_bar.low
  SHORT:
    favorable_price = current_bar.low
    adverse_price   = current_bar.high

  mfe_r = (favorable_price - trade.entry_price) / trade.initial_risk_r_price
  mae_r = (trade.entry_price - adverse_price)  / trade.initial_risk_r_price

  Update trade.MFE_r = max(trade.MFE_r, mfe_r)
  Update trade.MAE_r = max(trade.MAE_r, abs(mae_r))

─── Method: get_trailing_stop() ───
  def get_trailing_stop(
      trade: Trade,
      recent_bars: List[dict]  ← 2 bars gần nhất
  ) -> Decimal
  
  LONG:  return min(recent_bars[-1]["low"], recent_bars[-2]["low"])
  SHORT: return max(recent_bars[-1]["high"], recent_bars[-2]["high"])
  Nếu chưa đủ 2 bars: return trade.stop_loss_price (dùng SL gốc)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 2: backend/app/strategy/scanner.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class CBXScanner:
Vòng lặp trung tâm của bot, chạy async liên tục.

─── Method: start() ───
  Khởi động AsyncIO loop với interval = BOT_SCAN_INTERVAL_SECONDS

─── Method: stop() ───
  Graceful shutdown — hoàn thành scan hiện tại trước khi dừng

─── Main scan loop ───
  while self._running:
      scan_start = now()
      
      for symbol in active_symbols:
          try:
              await self._scan_symbol(symbol)
          except Exception as e:
              logger.error(module="scanner", symbol=symbol, error=str(e))
              # KHÔNG raise — lỗi 1 symbol không crash loop
      
      elapsed = now() - scan_start
      sleep_time = max(0, BOT_SCAN_INTERVAL_SECONDS - elapsed)
      await asyncio.sleep(sleep_time)

─── Method: _scan_symbol() ───
Signature:
  async def _scan_symbol(self, symbol: str) -> None

Flow đầy đủ:

BƯỚC 1 — Fetch data:
  df_15m = await data_fetcher.get_klines(symbol, "15m", limit=200)
  df_1h  = await data_fetcher.get_klines(symbol, "1h",  limit=2160)
  Nếu thiếu data → log warning, return sớm

BƯỚC 2 — Tính features:
  df_15m = feature_engine.compute(df_15m, df_1h, config)
  df_15m = percentile_engine.compute(df_15m, config)
  Lưu percentile vào PERCENTILE_CACHE (async, non-blocking)

BƯỚC 3 — Context Filter (chạy trên 1h):
  context_result = context_filter.check(df_1h, "LONG", ...)
  Lưu vào CONTEXT_FILTER_LOG và MARKET_REGIME_LOG

BƯỚC 4 — Update open trades TRƯỚC khi check signal mới:
  open_trades = await db.query Trade WHERE symbol=symbol, status=OPEN
  for trade in open_trades:
      recent_bars = df_15m[-3:].to_dict("records")
      action = trade_manager.update(trade, current_bar, zone, config)
      trade_manager.update_mfe_mae(trade, current_bar)
      
      if action.action_type != "HOLD":
          await self._execute_trade_action(trade, action)

BƯỚC 5 — Compression detection:
  zone = compression_detector.detect(df_15m, run_id, symbol_id)
  Nếu không có zone active → return (không check breakout)

BƯỚC 6 — Context filter cho side cụ thể:
  for side in ["LONG", "SHORT"]:
      ctx = context_filter.check(df_1h, side, zone, config)
      await context_filter.save_log(ctx, event_id, run_id, db)
      if not ctx.allowed: continue

BƯỚC 7 — Breakout detection:
  current_bar = df_15m.iloc[-1].to_dict()
  breakout = breakout_detector.detect(current_bar, zone, df_15m.iloc[-1], config)
  await breakout_detector.save_event(breakout, event_id, run_id, db)
  await breakout_detector.save_filter_logs(breakout, event_id, run_id, db)
  if not breakout.is_valid: return

BƯỚC 8 — Expansion validation (async task, không block):
  asyncio.create_task(
      self._wait_for_expansion(breakout, zone, symbol, context_result, run_id)
  )

─── Method: _wait_for_expansion() ───
  Chờ tối đa expansion_lookforward_bars (3) bars
  Collect các bars tiếp theo qua polling (sleep 15m interval)
  expansion = expansion_validator.validate(breakout, next_bars, zone, config)
  await expansion_validator.save_event(expansion, breakout_id, run_id, db)
  
  if expansion.is_confirmed:
      await self._handle_signal(expansion, breakout, zone, symbol, run_id)

─── Method: _handle_signal() ───
  Tạo signal object, lưu vào Redis (TTL=15 phút)
  Broadcast WebSocket event "signal_detected"
  
  if BOT_MODE == "auto":
      await self._execute_entry(expansion, breakout, zone, symbol, run_id)
  else:  # manual
      await notification_service.notify_signal(signal)
      # Chờ user action qua Telegram hoặc Web

─── Method: _execute_entry() ───
  risk_check = await risk_engine.check_can_trade(symbol_id, side, db)
  if not risk_check.allowed:
      logger.info("Entry blocked by risk engine", reason=risk_check.block_reason)
      return

  equity = await binance_client.get_account_balance()
  entry_order = entry_engine.prepare_entry(expansion, breakout, zone, entry_model, config)
  
  if not entry_engine.is_still_valid(entry_order, current_bar):
      logger.info("Entry invalidated before execution")
      return

  size_result = risk_engine.calculate_position_size(
      entry_order.entry_price_estimate, entry_order.stop_loss_price,
      equity, config, exchange_config
  )
  if not size_result.valid:
      logger.warning("Position size invalid", reason=size_result.invalid_reason)
      return

  # Tạo Trade record TRƯỚC khi gửi lệnh
  trade = Trade(status="PENDING", ...)
  db.add(trade)
  await db.commit()

  # Gửi lệnh (TESTNET hoặc LIVE tùy .env)
  order_result = await order_executor.place_market_order(
      symbol, side, size_result.qty
  )
  
  # Update trade status
  trade.status = "OPEN"
  trade.entry_price = order_result.filled_price
  await db.commit()
  
  await risk_engine.update_session_on_open(symbol_id, run_id, db)
  await notification_service.notify_trade_opened(trade)

─── Method: _execute_trade_action() ───
  Thực thi TradeAction từ TradeManager:
  
  if action.exit_type == "PARTIAL_1R":
      order = await order_executor.place_market_order(
          symbol, opposite_side, action.size_to_close
      )
      # Ghi EXIT_EVENT, update trade.partial_exit_done=True
  
  else:  # CLOSE_FULL
      remaining_size = trade.position_size - trade.partial_closed_size
      order = await order_executor.place_market_order(
          symbol, opposite_side, remaining_size
      )
      # Tính pnl_r, ghi EXIT_EVENT, update trade.status=CLOSED
      trade_result = "FAILED_BREAKOUT" if pnl_r < 0 else "WIN"
      await risk_engine.update_session_on_close(
          symbol_id, run_id, pnl_r, trade_result, db
      )
      await notification_service.notify_trade_closed(trade, pnl_r)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File 1: backend/tests/test_trade_manager.py (8 cases)

Test 1: STOP_LOSS triggered LONG
  trade.stop_loss=49900, current_bar.low=49850
  → action_type="CLOSE_FULL", exit_type="STOP_LOSS"

Test 2: STOP_LOSS triggered SHORT
  trade.stop_loss=50100, current_bar.high=50150
  → action_type="CLOSE_FULL", exit_type="STOP_LOSS"

Test 3: STRUCTURE_FAIL LONG
  current_bar.close < zone.low
  → action_type="CLOSE_FULL", exit_type="STRUCTURE_FAIL"

Test 4: TIME_STOP
  trade.hold_bars=8, total_pnl_r=0.3 (< 1R)
  → action_type="CLOSE_FULL", exit_type="TIME_STOP"

Test 5: TIME_STOP NOT triggered — đã đạt 1R
  trade.hold_bars=8, total_pnl_r=1.2 (> 1R)
  → action_type="HOLD" (không time stop vì đã lãi)

Test 6: PARTIAL_1R triggered
  trade.partial_exit_done=False, current_bar.high >= tp1_price
  → action_type="CLOSE_PARTIAL", exit_type="PARTIAL_1R"
  → size_to_close = position_size × 0.5

Test 7: TRAILING triggered sau partial
  trade.partial_exit_done=True
  recent_bars: bar[-1].low=49800, bar[-2].low=49750
  trailing_stop = min(49800, 49750) = 49750
  current_bar.low = 49700 <= 49750
  → action_type="CLOSE_FULL", exit_type="TRAILING"

Test 8: HOLD — không có điều kiện nào triggered
  Giá đang ở giữa, hold_bars=3, chưa đạt 1R
  → action_type="HOLD"
  Verify: MFE_r và MAE_r được cập nhật đúng

File 2: backend/tests/test_scanner.py (3 cases — integration tests)

Test 1: Full pipeline LONG signal
  Mock df_15m với synthetic compression + breakout + expansion
  Mock df_1h với EMA50 context favorable
  Chạy _scan_symbol() với mode="manual"
  Assert:
  - CompressionEvent ghi vào DB
  - BreakoutEvent ghi vào DB với is_valid=True
  - ExpansionEvent ghi vào DB với is_confirmed=True
  - Signal lưu vào Redis
  - KHÔNG có Trade nào được tạo (manual mode)

Test 2: Pipeline bị chặn bởi Context Filter
  Mock df_1h với EMA50 blocking LONG (close < EMA50, slope âm)
  Assert:
  - ContextFilterLog ghi với decision="BLOCKED"
  - Không có BreakoutEvent nào được tạo

Test 3: Error isolation
  Mock symbol "BTCUSDC" để throw Exception khi fetch data
  Chạy scan loop với ["BTCUSDC", "SOLUSDC"]
  Assert:
  - BTCUSDC log error
  - SOLUSDC vẫn được scan bình thường (không bị ảnh hưởng)

Chạy:
  python -m pytest backend/tests/test_trade_manager.py -v
  python -m pytest backend/tests/test_scanner.py -v
Expected: 8/8 + 3/3 = 11 PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ LƯU Ý QUAN TRỌNG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Scanner test dùng mock hoàn toàn — KHÔNG gọi Binance API thật
2. BINANCE_TESTNET=true trong .env khi chạy integration
3. Trade record được tạo TRƯỚC khi gửi lệnh (status=PENDING)
   → Nếu Binance API fail, trade ở PENDING, không bị mất track
4. _wait_for_expansion() chạy trong asyncio.create_task
   → Không block scan loop của symbol khác
5. Mỗi symbol trong try/except riêng — đây là yêu cầu bắt buộc