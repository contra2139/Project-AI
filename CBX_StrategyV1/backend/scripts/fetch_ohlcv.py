import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import pandas as pd
from sqlalchemy import text, create_mock_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.symbol import SymbolRegistry, SymbolExchangeConfig, SymbolStrategyConfig
from app.database import Base

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

SYMBOLS = ["BTCUSDC", "BNBUSDC", "SOLUSDC"]
TIMEFRAMES = ["15m", "1h"]
START_DATE = "1 Jan, 2024"
END_DATE = "28 Feb, 2026"

async def init_db(session: AsyncSession):
    """Create tables if they don't exist."""
    # Create Base tables (models)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create raw OHLCV tables if not exist
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS ohlcv_15m (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(18, 8) NOT NULL,
            high DECIMAL(18, 8) NOT NULL,
            low DECIMAL(18, 8) NOT NULL,
            close DECIMAL(18, 8) NOT NULL,
            volume DECIMAL(20, 8) NOT NULL
        )
    """))
    # Fix for SQLite: SERIAL -> INTEGER PRIMARY KEY AUTOINCREMENT
    if "sqlite" in DATABASE_URL:
        await session.execute(text("DROP TABLE IF EXISTS ohlcv_15m"))
        await session.execute(text("DROP TABLE IF EXISTS ohlcv_1h"))
        await session.execute(text("""
            CREATE TABLE ohlcv_15m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol VARCHAR(20) NOT NULL,
                timestamp DATETIME NOT NULL,
                open DECIMAL(18, 8) NOT NULL,
                high DECIMAL(18, 8) NOT NULL,
                low DECIMAL(18, 8) NOT NULL,
                close DECIMAL(18, 8) NOT NULL,
                volume DECIMAL(20, 8) NOT NULL
            )
        """))
        await session.execute(text("""
            CREATE TABLE ohlcv_1h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol VARCHAR(20) NOT NULL,
                timestamp DATETIME NOT NULL,
                open DECIMAL(18, 8) NOT NULL,
                high DECIMAL(18, 8) NOT NULL,
                low DECIMAL(18, 8) NOT NULL,
                close DECIMAL(18, 8) NOT NULL,
                volume DECIMAL(20, 8) NOT NULL
            )
        """))
    else:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS ohlcv_1h (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DECIMAL(18, 8) NOT NULL,
                high DECIMAL(18, 8) NOT NULL,
                low DECIMAL(18, 8) NOT NULL,
                close DECIMAL(18, 8) NOT NULL,
                volume DECIMAL(20, 8) NOT NULL
            )
        """))
    await session.commit()

async def register_symbols(session: AsyncSession):
    """Ensure symbols and their configs exist in registry."""
    for sym_name in SYMBOLS:
        res = await session.execute(text("SELECT symbol_id FROM symbol_registry WHERE symbol = :s"), {"s": sym_name})
        row = res.fetchone()
        
        if not row:
            logger.info(f"Registering {sym_name}...")
            symbol_id = uuid.uuid4()
            sym = SymbolRegistry(
                symbol_id=symbol_id,
                symbol=sym_name,
                base_asset=sym_name.replace("USDC", ""),
                quote_asset="USDC",
                exchange="Binance",
                contract_type="PERPETUAL"
            )
            session.add(sym)
            await session.flush()
            
            # Add default configs
            ex_cfg = SymbolExchangeConfig(
                symbol_id=symbol_id,
                lot_size_step=Decimal("0.001"),
                min_qty=Decimal("0.001"),
                min_notional=Decimal("5.0"),
                price_tick_size=Decimal("0.1"),
                maker_fee_pct=Decimal("0.0002"),
                taker_fee_pct=Decimal("0.0005"),
                default_leverage=10,
                max_leverage=50,
                margin_type="ISOLATED",
                source="MANUAL"
            )
            strat_cfg = SymbolStrategyConfig(
                symbol_id=symbol_id,
                version=1,
                created_by="FetchScript"
            )
            session.add(ex_cfg)
            session.add(strat_cfg)
            await session.commit()
        else:
            logger.info(f"Symbol {sym_name} already registered.")

async def fetch_and_store(client: AsyncClient, session: AsyncSession):
    """Fetch OHLCV data from Binance and store in DB."""
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            table = f"ohlcv_{tf}"
            logger.info(f"Fetching {tf} data for {symbol}...")
            
            # Clear existing data for a clean fresh fetch as requested for the new range
            # Whitelist check for SQL safety
            ALLOWED_TABLES = ["ohlcv_15m", "ohlcv_1h"]
            if table not in ALLOWED_TABLES:
                raise ValueError(f"Unauthorized table access: {table}")
            await session.execute(text(f"DELETE FROM {table} WHERE symbol = :s"), {"s": symbol})
            await session.commit()
            logger.info(f"Cleared existing {tf} data for {symbol} for fresh 2024-2026 fetch.")

            try:
                klines = await client.get_historical_klines(
                    symbol,
                    tf,
                    START_DATE,
                    END_DATE
                )
                
                if not klines:
                    logger.warning(f"No data returned for {symbol} {tf}")
                    continue

                logger.info(f"{symbol} {tf}: Fetched {len(klines)} candles.")
                
                # Report data range
                first_ts = datetime.fromtimestamp(klines[0][0]/1000)
                last_ts = datetime.fromtimestamp(klines[-1][0]/1000)
                logger.info(f"📊 {symbol} {tf}: {len(klines)} nến từ {first_ts.strftime('%Y-%m-%d')} đến {last_ts.strftime('%Y-%m-%d')}")

                # Batch insert
                data_list = []
                for k in klines:
                    data_list.append({
                        "symbol": symbol,
                        "timestamp": datetime.fromtimestamp(k[0]/1000),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                
                # Chunked insert for large datasets
                chunk_size = 1000
                for i in range(0, len(data_list), chunk_size):
                    chunk = data_list[i : i+chunk_size]
                    stmt = text(f"INSERT INTO {table} (symbol, timestamp, open, high, low, close, volume) VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume)")
                    await session.execute(stmt, chunk)
                
                await session.commit()
                logger.info(f"Successfully ingested {len(data_list)} rows into {table} for {symbol}.")

            except BinanceAPIException as e:
                logger.error(f"Binance Error for {symbol} {tf}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error for {symbol} {tf}: {e}")

async def main():
    async with AsyncSessionLocal() as session:
        await init_db(session)
        await register_symbols(session)
        
        # Binance Client
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        client = await AsyncClient.create(api_key, api_secret)
        
        try:
            await fetch_and_store(client, session)
        finally:
            await client.close_connection()
            await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
