CBX Trading Bot — Python FastAPI, PostgreSQL.

Giai đoạn 3 đã hoàn thành:
- simulator.py     (FillSimulator)
- engine.py        (BacktestEngine, BacktestConfig, BacktestRunResult)
- reporter.py      (BacktestReporter, BacktestSummary)

BacktestEngine.run(config) nhận BacktestConfig và trả về BacktestRunResult.
BacktestSummary có: total_trades, win_rate, total_pnl_r, max_drawdown_r,
profit_factor, long_pnl_r, short_pnl_r, exit_breakdown

WalkForwardWindow DB model có:
  window_id, wf_experiment_id, symbol_id, window_index,
  train_start, train_end, test_start, test_end,
  train_run_id, test_run_id,
  train_pnl_r, test_pnl_r, train_win_rate, test_win_rate,
  efficiency_ratio, best_params_json, overfitting_flag

Yêu cầu bắt buộc:
1. Decimal cho mọi số
2. Async/await cho DB
3. Không hardcode threshold — đọc từ config