Tạo Backtest Engine cho CBX Bot.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 1: backend/app/backtest/simulator.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class FillSimulator:
Mô phỏng việc fill lệnh trong backtest.

─── Method: simulate_entry_fill() ───
Signature:
  def simulate_entry_fill(
      entry_bar: dict,    ← bar ngay sau confirmation bar
      side: str,
      atr_value: Decimal,
      slippage_atr_pct: Decimal = Decimal("0.05")
  ) -> Decimal

Logic:
  base_price = Decimal(str(entry_bar["open"]))
  slippage   = atr_value × slippage_atr_pct
  LONG:  fill_price = base_price + slippage  ← mua cao hơn open
  SHORT: fill_price = base_price - slippage  ← bán thấp hơn open

─── Method: simulate_stop_hit() ───
Signature:
  def simulate_stop_hit(
      trade_side: str,
      stop_price: Decimal,
      bar: dict
  ) -> tuple[bool, Decimal]

Logic:
  LONG:  hit = bar["low"] <= stop_price
         fill = stop_price (assume fill at stop, worst case)
  SHORT: hit = bar["high"] >= stop_price
         fill = stop_price
  Return: (hit: bool, fill_price: Decimal)

─── Method: simulate_partial_fill() ───
  LONG/SHORT: fill tại tp1_price (giả định đạt được nếu bar chạm)

─── Method: calculate_fees() ───
  fee = qty × fill_price × taker_fee_pct
  Tính cho cả entry và exit, cộng vào total_fees_usd

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 2: backend/app/backtest/engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class BacktestEngine:

─── Method: run() ───
Signature:
  async def run(config: BacktestConfig) -> BacktestRunResult

BacktestConfig dataclass:
  symbol_id: UUID
  strategy_config_id: UUID
  data_start: datetime
  data_end: datetime
  entry_model: str          ← "FOLLOW_THROUGH", "RETEST", hoặc "BOTH"
  side_filter: str          ← "LONG_ONLY", "SHORT_ONLY", hoặc "BOTH"
  run_name: str
  slippage_atr_pct: Decimal (default 0.05)
  initial_equity: Decimal   (default Decimal("10000"))

Flow:

BƯỚC 1 — Setup:
  INSERT RESEARCH_RUN (mode=BACKTEST, status=RUNNING)
  Load toàn bộ OHLCV 15m và 1h từ data_start đến data_end
  Tính features một lần cho toàn bộ data

  CRITICAL — Tính percentile ĐÚNG CÁCH:
  Dùng expanding window cho 120 bar đầu (warmup period)
  Sau đó rolling(120) thuần túy
  Lưu vào PERCENTILE_CACHE với is_expanding flag
  TUYỆT ĐỐI không tính percentile trên toàn dataset trước

BƯỚC 2 — Simulation loop:
  equity = initial_equity
  open_trades = []
  session_state = MockSessionState()  ← in-memory, không cần DB trong loop

  for i in range(warmup_period, len(df_15m)):
      current_bar   = df_15m.iloc[i]
      visible_data  = df_15m.iloc[:i+1]   ← chỉ thấy đến bar i
      visible_1h    = df_1h[df_1h.time <= current_bar.time]

      # Update open trades trước
      for trade in open_trades[:]:
          action = trade_manager.update(trade, current_bar, zone, config)
          if action.action_type != "HOLD":
              fill = simulator.simulate_stop_hit(...)
              _close_trade(trade, fill, action, equity)
              equity = _update_equity(trade)
              open_trades.remove(trade)

      # Check new signal
      zone = compression_detector.detect(visible_data, ...)
      if not zone or not zone.is_active: continue

      ctx = context_filter.check(visible_1h.iloc[-1:], side, zone, config)
      if not ctx.allowed: continue

      breakout = breakout_detector.detect(current_bar, zone, ...)
      if not breakout.is_valid: continue

      # Expansion: dùng 3 bars tiếp theo (i+1, i+2, i+3)
      next_bars = df_15m.iloc[i+1:i+4].to_dict("records")
      if len(next_bars) < 1: continue
      expansion = expansion_validator.validate(breakout, next_bars, zone, config)
      if not expansion.is_confirmed: continue

      # Risk check (dùng mock session, không DB)
      if not session_state.can_trade(side): continue

      # Entry
      entry_bar  = df_15m.iloc[i + expansion.confirmation_bar_index + 1]
      fill_price = simulator.simulate_entry_fill(entry_bar, side, zone.atr_value)
      stop_price = risk_engine.calculate_stop_loss(side, zone, breakout.breakout_bar, config)
      size       = risk_engine.calculate_position_size(fill_price, stop_price, equity, config, exchange_config)

      if not size.valid: continue

      trade = _create_trade(fill_price, stop_price, size, entry_model, side)
      open_trades.append(trade)
      session_state.open_position_count += 1

BƯỚC 3 — Ghi kết quả:
  Sau khi loop kết thúc, force-close tất cả open_trades tại giá đóng cuối
  Ghi tất cả events và trades vào DB với run_id
  Tính summary metrics
  UPDATE RESEARCH_RUN (status=COMPLETED, + tất cả KPIs)

─── Method: _close_trade() ───
  Tính pnl_r = (exit_price - entry_price) / initial_risk_r_price (LONG)
  Tính pnl_usd = pnl_r × risk_amount_usd - fees
  Ghi EXIT_EVENT vào DB
  Update Trade (status=CLOSED)
  Update MockSessionState

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 3: backend/app/backtest/reporter.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class BacktestReporter:

─── Method: generate_summary() ───
Signature:
  async def generate_summary(run_id: UUID) -> BacktestSummary

BacktestSummary dataclass với các metrics:

  Tổng quan:
  - total_trades, win_count, loss_count
  - win_rate: Decimal  ← win_count / total_trades
  - total_pnl_r, total_pnl_usd
  - profit_factor: Decimal  ← sum(wins_r) / abs(sum(losses_r))

  Risk metrics:
  - max_drawdown_r     ← max peak-to-trough trong equity curve
  - max_consecutive_losses
  - avg_mfe_r, avg_mae_r

  Efficiency:
  - avg_hold_bars
  - avg_win_r, avg_loss_r

  Breakdown theo exit type:
  - exit_breakdown: dict  ← {"STOP_LOSS": N, "TRAILING": N, ...}

  Breakdown theo side:
  - long_trades, long_win_rate, long_pnl_r
  - short_trades, short_win_rate, short_pnl_r

─── Method: print_report() ───
  In ra console theo format dễ đọc:
═══════════════════════════════════
CBX BACKTEST RESULTS — BTCUSDC
Run: {run_name} | {data_start} → {data_end}
═══════════════════════════════════
Trades:    {total} ({wins}W / {losses}L)
Win Rate:  {win_rate:.1%}
Total PnL: {total_pnl_r:+.2f}R  (${total_pnl_usd:+.0f})
Max DD:    {max_drawdown_r:.2f}R
PF:        {profit_factor:.2f}
LONG:  {long_trades} trades | WR {long_win_rate:.1%} | {long_pnl_r:+.2f}R
SHORT: {short_trades} trades | WR {short_win_rate:.1%} | {short_pnl_r:+.2f}R
Exit breakdown:
STOP_LOSS:     {n} ({pct:.0%})
TRAILING:      {n} ({pct:.0%})
PARTIAL_1R:    {n} ({pct:.0%})
TIME_STOP:     {n} ({pct:.0%})
STRUCTURE_FAIL:{n} ({pct:.0%})
═══════════════════════════════════
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: backend/tests/test_backtest_engine.py (5 cases)

Test 1: No look-ahead bias
  Tạo 150 bars synthetic data
  Tính percentile tại bar 50
  Verify: percentile chỉ dùng bars 0–50, KHÔNG dùng bars 51–149
  Cách verify: percentile(bar_50) với full data ≠ percentile(bar_50) với 51 bars
  Assert: kết quả expanding window khác với kết quả full-data calculation

Test 2: Slippage applied correctly
  LONG entry: entry_bar.open=50000, atr=200, slippage_pct=0.05
  fill = 50000 + (200 × 0.05) = 50010
  Assert: fill_price == Decimal("50010")

Test 3: Full backtest run — smoke test
  Tạo synthetic data 500 bars với 2 compression zones rõ ràng
  Chạy BacktestEngine.run() với LONG_ONLY, FOLLOW_THROUGH
  Assert:
  - RESEARCH_RUN được tạo với status=COMPLETED
  - Có ít nhất 1 trade trong DB
  - total_pnl_r là Decimal (không phải float)
  - max_drawdown_r <= 0 (drawdown luôn âm hoặc bằng 0)

Test 4: Equity curve đúng hướng
  Mock 3 trades: +1R, -1R, +2R
  Assert: equity_snapshots tăng sau trade 1, giảm sau trade 2, tăng sau trade 3
  Assert: final equity = initial + net_pnl_usd

Test 5: Side separation
  Chạy backtest LONG_ONLY và SHORT_ONLY riêng
  Assert: LONG_ONLY run không có SHORT trade nào
  Assert: SHORT_ONLY run không có LONG trade nào

Chạy: python -m pytest backend/tests/test_backtest_engine.py -v
Expected: 5/5 PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. visible_data = df_15m.iloc[:i+1] — bắt buộc, không dùng df_15m toàn bộ
2. Warmup period = 120 bars — không trade trong giai đoạn này
3. Expansion dùng next_bars = df_15m.iloc[i+1:i+4] — không dùng confirmed bars
4. Force-close tất cả open trades ở bar cuối cùng (không để treo)
5. Fees tính 2 lần: khi vào và khi thoát