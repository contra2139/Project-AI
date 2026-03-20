CBX Trading Bot — Python FastAPI, PostgreSQL, Redis, Binance Futures API.
KHÔNG dùng CCXT. Data fetching qua python-binance SDK.

Đã hoàn thành:
- feature_engine.py     (ATR, BB, range, EMA50, realized_vol)
- percentile_engine.py  (rolling percentile, no look-ahead)
- compression_detector.py
- breakout_detector.py
- expansion_validator.py

CompressionZone có: high, low, atr_value, width_pct
BreakoutResult có: side ("LONG"/"SHORT"), breakout_price_level
ExpansionResult có: is_confirmed, max_extension_atr

SymbolStrategyConfig có:
- ema_period_context: int (default 50)
- context_timeframe: str (default "1h")
- execution_timeframe: str (default "15m")

Yêu cầu bắt buộc:
1. Decimal cho số giá, không float
2. Async/await cho DB
3. Không hardcode, đọc từ config
4. Log structured JSON