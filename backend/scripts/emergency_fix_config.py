import os
import sys
import sqlite3
import uuid
from datetime import datetime

# BƯỚC 1 — Tìm đúng file DB đang được dùng
# Thêm đường dẫn gốc vào sys.path để import được app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from backend.app.config import Settings
    settings = Settings()
    print(f"DATABASE_URL from settings: {settings.DATABASE_URL}")
except ImportError as e:
    print(f"Error importing Settings: {e}")
    # Fallback nếu không import được
    class MockSettings:
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///test.db")
    settings = MockSettings()
    print(f"Fallback DATABASE_URL: {settings.DATABASE_URL}")

# BƯỚC 2 — Kết nối trực tiếp và INSERT config
# Xử lý URL SQLite
db_url = settings.DATABASE_URL
if "sqlite" in db_url:
    db_path = db_url.replace("sqlite+aiosqlite:///", "")
    db_path = db_path.replace("sqlite:///", "")
    # Xử lý path tương đối/tuyệt đối
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', db_path))
    
    print(f"DB Path resolved to: {db_path}")
    print(f"DB file exists: {os.path.exists(db_path)}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
else:
    print("Postgres detected. This emergency script currently only supports SQLite locally.")
    sys.exit(1)

# Kiểm tra tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables in DB: {tables}")

# Kiểm tra symbols
cursor.execute("SELECT symbol_id, symbol FROM symbol_registry")
symbols_in_db = cursor.fetchall()
print(f"Symbols found in registry: {symbols_in_db}")

# BƯỚC 3 — INSERT config trực tiếp cho từng symbol
SYMBOLS_MAP = {
    'BTCUSDC': None,
    'BNBUSDC': None,
    'SOLUSDC': None
}

# Lấy symbol_ids từ DB
for symbol in SYMBOLS_MAP:
    cursor.execute(
        "SELECT symbol_id FROM symbol_registry WHERE symbol=?",
        (symbol,)
    )
    row = cursor.fetchone()
    if row:
        SYMBOLS_MAP[symbol] = row[0]
        print(f"  {symbol}: {row[0]}")
    else:
        print(f"  {symbol}: NOT FOUND IN DB - Please run registration first.")

# Deactivate tất cả config cũ
cursor.execute("UPDATE symbol_strategy_config SET is_current=0")

# Insert config V4 cho từng symbol
for symbol, symbol_id in SYMBOLS_MAP.items():
    if symbol_id is None:
        print(f"SKIP {symbol}: no symbol_id")
        continue
    
    config_id = str(uuid.uuid4())
    
    # SOL dùng RETEST, BTC/BNB dùng FOLLOW_THROUGH
    entry_model = 'RETEST' if symbol == 'SOLUSDC' else 'FOLLOW_THROUGH'
    
    print(f"Inserting V4 config for {symbol}...")
    cursor.execute("""
        INSERT INTO symbol_strategy_config (
            strategy_config_id, symbol_id, version, is_current,
            name, created_at, created_by,
            atr_period, atr_percentile_window, atr_percentile_threshold,
            range_bars, range_percentile_threshold,
            bb_period, bb_std, bb_width_percentile_threshold,
            volume_percentile_threshold,
            compression_min_bars, compression_max_bars, min_conditions_met,
            breakout_distance_min_atr, breakout_body_ratio_min,
            breakout_close_position_long, breakout_close_position_short,
            breakout_volume_ratio_min, breakout_volume_percentile_min,
            breakout_bar_size_max_atr, false_break_limit,
            expansion_lookforward_bars, expansion_body_loss_max_pct,
            retest_max_bars, stop_loss_atr_buffer,
            partial_exit_r_level, partial_exit_pct,
            time_stop_bars, ema_period_context,
            context_timeframe, execution_timeframe,
            risk_per_trade_pct, max_position_per_symbol
        ) VALUES (
            ?, ?, 4, 1,
            ?, ?, 'RESEARCHER',
            14, 120, 20.0,
            12, 20.0,
            20, 2.0, 20.0,
            60.0,
            8, 24, 3,
            0.20, 0.50,
            0.65, 0.35,
            1.10, 60.0,
            2.50, 2,
            3, 50.0,
            3, 0.20,
            0.80, 0.30,
            30, 50,
            '1h', '15m',
            0.0025, 1
        )
    """, (
        config_id, str(symbol_id),
        f"{symbol} V4 Emergency Fix",
        datetime.now().isoformat()
    ))
    print(f"  Result: OK | ID: {config_id}")

conn.commit()

# Verify
print("\n=== VERIFY ACTIVE CONFIGS ===")
cursor.execute("""
    SELECT sr.symbol, sc.version, sc.is_current, sc.time_stop_bars, sc.risk_per_trade_pct
    FROM symbol_strategy_config sc
    JOIN symbol_registry sr ON sc.symbol_id = sr.symbol_id
    WHERE sc.is_current = 1
""")
result = cursor.fetchall()
for row in result:
    print(f"  {row[0]}: version={row[1]}, is_current={row[2]}, time_stop={row[3]}, risk={row[4]}")

conn.close()
print("\nDone. Run backtest now.")
