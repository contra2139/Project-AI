Tạo Walk-Forward Validation cho CBX Bot.

File: backend/app/backtest/walk_forward.py

━━━ MỤC ĐÍCH ━━━
Kiểm tra xem chiến lược có thực sự robust hay chỉ overfit
trên dữ liệu cụ thể. Chia data thành nhiều windows,
mỗi window có in-sample (train) và out-of-sample (test).

━━━ WalkForwardConfig dataclass ━━━
  symbol_id: UUID
  strategy_config_id: UUID
  total_start: datetime       ← toàn bộ data bắt đầu từ đây
  total_end: datetime         ← toàn bộ data kết thúc ở đây
  train_months: int           ← default 4
  test_months: int            ← default 1
  step_months: int            ← default 1 (rolling forward)
  side_filter: str            ← "LONG_ONLY", "SHORT_ONLY", "BOTH"
  entry_model: str
  initial_equity: Decimal
  overfitting_threshold: Decimal  ← default 0.5
  experiment_name: str

━━━ Method: run() ━━━
Signature:
  async def run(config: WalkForwardConfig) -> WalkForwardResult

BƯỚC 1 — Tạo windows:
  windows = []
  current_start = config.total_start

  while True:
      train_end = current_start + relativedelta(months=config.train_months)
      test_end  = train_end + relativedelta(months=config.test_months)

      if test_end > config.total_end: break

      windows.append({
          "window_index": len(windows) + 1,
          "train_start":  current_start,
          "train_end":    train_end,
          "test_start":   train_end,
          "test_end":     test_end
      })
      current_start += relativedelta(months=config.step_months)

  Nếu len(windows) < 2:
      raise ValueError("Không đủ data để tạo ít nhất 2 windows")

BƯỚC 2 — Chạy backtest cho từng window:
  wf_experiment_id = uuid4()

  for window in windows:
      # IN-SAMPLE (train)
      train_config = BacktestConfig(
          symbol_id=config.symbol_id,
          data_start=window["train_start"],
          data_end=window["train_end"],
          run_name=f"{config.experiment_name}_W{window['window_index']}_TRAIN",
          ...
      )
      train_result = await backtest_engine.run(train_config)

      # OUT-OF-SAMPLE (test) — CÙNG config, không optimize lại
      test_config = BacktestConfig(
          symbol_id=config.symbol_id,
          data_start=window["test_start"],
          data_end=window["test_end"],
          run_name=f"{config.experiment_name}_W{window['window_index']}_TEST",
          ...
      )
      test_result = await backtest_engine.run(test_config)

      # Tính efficiency ratio
      if train_result.total_pnl_r > 0:
          efficiency_ratio = test_result.total_pnl_r / train_result.total_pnl_r
      else:
          efficiency_ratio = Decimal("0")

      overfitting_flag = efficiency_ratio < config.overfitting_threshold

      # Ghi vào DB
      wf_window = WalkForwardWindow(
          wf_experiment_id=wf_experiment_id,
          symbol_id=config.symbol_id,
          window_index=window["window_index"],
          train_start=window["train_start"],
          train_end=window["train_end"],
          test_start=window["test_start"],
          test_end=window["test_end"],
          train_run_id=train_result.run_id,
          test_run_id=test_result.run_id,
          train_pnl_r=train_result.total_pnl_r,
          test_pnl_r=test_result.total_pnl_r,
          train_win_rate=train_result.win_rate,
          test_win_rate=test_result.win_rate,
          efficiency_ratio=efficiency_ratio,
          overfitting_flag=overfitting_flag
      )
      db.add(wf_window)
      await db.commit()

BƯỚC 3 — Aggregate kết quả:
  avg_efficiency   = mean của tất cả efficiency_ratio
  pct_overfit      = số windows có overfitting_flag / tổng windows
  is_robust        = avg_efficiency >= config.overfitting_threshold
                     VÀ pct_overfit <= 0.5

  Return WalkForwardResult

━━━ WalkForwardResult dataclass ━━━
  wf_experiment_id: UUID
  total_windows: int
  windows: List[WalkForwardWindowSummary]
  avg_train_pnl_r: Decimal
  avg_test_pnl_r: Decimal
  avg_efficiency_ratio: Decimal
  pct_overfitting_windows: Decimal
  is_robust: bool
  verdict: str   ← tự generate dựa trên is_robust và metrics

━━━ WalkForwardWindowSummary dataclass ━━━
  window_index: int
  train_period: str      ← "2024-01 → 2024-05"
  test_period: str       ← "2024-05 → 2024-06"
  train_pnl_r: Decimal
  test_pnl_r: Decimal
  efficiency_ratio: Decimal
  overfitting_flag: bool

━━━ Method: print_report() ━━━
  In ra console:
══════════════════════════════════════════
WALK-FORWARD VALIDATION — BTCUSDC
Experiment: {name} | Windows: {N}
══════════════════════════════════════════
Window  Train Period      Test Period       Train R  Test R   Eff.Ratio  Flag
──────────────────────────────────────────────────────────────────────────────
W1      Jan→May 2024      May→Jun 2024      +3.2R    +1.8R    0.56       ✅
W2      Feb→Jun 2024      Jun→Jul 2024      +2.8R    +0.9R    0.32       ⚠️
W3      Mar→Jul 2024      Jul→Aug 2024      +4.1R    +2.3R    0.56       ✅
──────────────────────────────────────────────────────────────────────────────
Avg Efficiency:  0.48
Overfit Windows: 1/3 (33%)
══════════════════════════════════════════
VERDICT: ⚠️ MARGINAL — Strategy shows mixed robustness.
2/3 windows pass efficiency threshold.
Consider reducing position size or additional filtering.
══════════════════════════════════════════
Verdict logic:
  - is_robust=True,  pct_overfit<=0.25 → "✅ ROBUST — Deploy with confidence"
  - is_robust=True,  pct_overfit<=0.50 → "⚠️ MARGINAL — Reduce position size"
  - is_robust=False                    → "❌ NOT ROBUST — Do not deploy"

━━━ TEST FILE ━━━
File: backend/tests/test_walk_forward.py (5 cases)

Test 1: Window generation đúng số lượng
  total_start = 2024-01-01, total_end = 2024-07-01
  train_months=4, test_months=1, step_months=1
  Expected windows: 2
  W1: train[Jan→May], test[May→Jun]
  W2: train[Feb→Jun], test[Jun→Jul]
  Assert: len(windows) == 2
  Assert: windows[0].train_start == datetime(2024,1,1)
  Assert: windows[1].test_end == datetime(2024,7,1)

Test 2: Efficiency ratio tính đúng
  Mock train_pnl_r=4.0, test_pnl_r=2.0
  Assert: efficiency_ratio == Decimal("0.5")

Test 3: Efficiency ratio khi train âm
  Mock train_pnl_r=-1.0 (strategy lỗ trong train)
  Assert: efficiency_ratio == Decimal("0")
  (Không chia cho số âm)

Test 4: Overfitting flag đúng
  overfitting_threshold=0.5
  efficiency_ratio=0.3 → overfitting_flag=True
  efficiency_ratio=0.7 → overfitting_flag=False

Test 5: is_robust logic
  3 windows: efficiency=[0.6, 0.3, 0.7]
  avg_efficiency = 0.533 >= 0.5 → True
  pct_overfit = 1/3 = 0.33 <= 0.5 → True
  Assert: is_robust=True
  Assert: verdict chứa "MARGINAL" (vì pct_overfit > 0.25)

Chạy: python -m pytest backend/tests/test_walk_forward.py -v
Expected: 5/5 PASSED