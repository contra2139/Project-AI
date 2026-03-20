CBX Trading Bot — Python FastAPI, PostgreSQL, Redis, Binance Futures.
Dùng python-binance SDK. KHÔNG dùng CCXT.

Đã hoàn thành toàn bộ Giai đoạn 2:
- feature_engine.py, percentile_engine.py
- compression_detector.py  → CompressionZone dataclass
- breakout_detector.py     → BreakoutResult dataclass
- expansion_validator.py   → ExpansionResult dataclass
- context_filter.py        → ContextFilterResult dataclass

SymbolStrategyConfig có các fields liên quan:
  risk_per_trade_pct: Decimal      (default 0.0025 = 0.25%)
  max_position_per_symbol: int     (default 1)
  stop_loss_atr_buffer: Decimal    (default 0.25)
  partial_exit_r_level: Decimal    (default 1.0)
  partial_exit_pct: Decimal        (default 0.50 = 50%)
  time_stop_bars: int              (default 8)
  retest_max_bars: int             (default 3)

Settings (từ .env) có:
  RISK_MAX_POSITIONS_PORTFOLIO: int   (default 2)
  RISK_DAILY_STOP_R: Decimal          (default -2.0)
  RISK_CONSECUTIVE_FAIL_STOP: int     (default 3)

SessionState DB model có:
  current_daily_pnl_r, consecutive_failures,
  open_position_count, trading_halted, halt_reason

Yêu cầu bắt buộc:
1. Decimal cho mọi số giá và tính toán tài chính
2. Async/await cho DB
3. Không hardcode — đọc từ config/settings
4. Log structured JSON mọi quyết định
5. BINANCE_TESTNET=true trong .env khi test