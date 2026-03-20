Tôi đang xây dựng CBX Trading Bot (Compression Breakout Expansion).
Stack: Python FastAPI, PostgreSQL, Redis, Binance Futures API.

Đã hoàn thành:
- feature_engine.py + percentile_engine.py (ATR, BB, range, volume percentile)
- compression_detector.py (State Machine, CompressionZone dataclass)
- breakout_detector.py (7 điều kiện + bộ lọc cấm, BreakoutResult dataclass)

BreakoutResult hiện có các fields:
  is_valid, side, invalid_reasons, condition_checks,
  breakout_price_level, breakout_distance_atr, bar_size_atr,
  body_to_range, close_position_in_candle,
  vol_ratio, vol_percentile, is_wick_dominant, breakout_bar (OHLCV dict)

CompressionZone hiện có:
  high (compression_high), low (compression_low),
  atr_value, width_pct, bar_count, false_break_count

Yêu cầu kỹ thuật bắt buộc:
1. Tất cả số giá dùng Python Decimal, không dùng float
2. Async/await cho DB operations
3. invalid_reasons là List[str], collect TẤT CẢ lý do fail
4. Không hardcode giá trị, đọc từ SymbolStrategyConfig
5. Log mọi quyết định với structured JSON