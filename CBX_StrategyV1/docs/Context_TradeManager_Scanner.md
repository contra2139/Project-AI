CBX Trading Bot — Python FastAPI, PostgreSQL, Redis, python-binance SDK.

Đã hoàn thành toàn bộ strategy modules:
- compression_detector.py  → CompressionZone
- breakout_detector.py     → BreakoutResult
- expansion_validator.py   → ExpansionResult
- context_filter.py        → ContextFilterResult
- risk_engine.py           → RiskCheckResult, PositionSizeResult
- entry_engine.py          → EntryOrder

EntryOrder có fields:
  symbol, side, entry_model, entry_price_estimate,
  stop_loss_price, tp1_price, initial_r_distance,
  zone_ref (CompressionZone), breakout_bar (dict OHLCV)

Trade DB model có:
  trade_id, symbol_id, side, entry_model, entry_price,
  stop_loss_price, initial_risk_r_price, position_size,
  status (OPEN/CLOSED/CANCELLED), MFE_r, MAE_r, hold_bars,
  exit_time, avg_exit_price, total_pnl_r, exit_model

SessionState DB model có:
  trading_halted, consecutive_failures, open_position_count,
  current_daily_pnl_r

Settings có:
  BOT_SCAN_INTERVAL_SECONDS: int (default 30)
  BOT_DEFAULT_MODE: str ("auto" hoặc "manual")
  TRADING_SYMBOLS: List[str]

Yêu cầu bắt buộc:
1. Decimal cho mọi số giá
2. Async/await cho tất cả DB và API calls
3. Không hardcode — đọc từ config/settings
4. Log structured JSON mọi quyết định
5. BINANCE_TESTNET=true khi test
6. Mỗi symbol scan trong try/except riêng — lỗi 1 symbol không crash symbol khác