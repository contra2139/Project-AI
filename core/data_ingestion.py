import asyncio
import sys
import pandas as pd
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
import logging

# Fix: aiodns requires SelectorEventLoop on Windows
# Python 3.8+ on Windows defaults to ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)

from core.binance_client import BinanceClientManager

async def fetch_klines(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
    """Tải klines từ Binance Futures sử dụng Shared Client."""
    try:
        client = await BinanceClientManager.get_client()
        klines = await client.futures_klines(symbol=symbol, interval=interval, limit=limit)

        if not klines:
            return pd.DataFrame()

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, axis=1)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df

    except BinanceAPIException as e:
        logger.error(f"Binance API Lỗi ({symbol} {interval}): {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Lỗi kéo nến {symbol} {interval}: {e}")
        return pd.DataFrame()

async def get_multi_timeframe_data(symbol: str, limit: int = 100) -> dict:
    """Kéo song song 3 khung: 4h, 1h, 15m. Trả về dict chứa 3 DataFrame."""
    try:
        results = await asyncio.gather(
            fetch_klines(symbol, "4h", limit),
            fetch_klines(symbol, "1h", limit),
            fetch_klines(symbol, "15m", limit)
        )
        
        return {
            "4h": results[0],
            "1h": results[1],
            "15m": results[2]
        }
    except Exception as e:
        logger.error(f"Lỗi khi chạy Async Gather cho {symbol}: {e}")
        return {"4h": pd.DataFrame(), "1h": pd.DataFrame(), "15m": pd.DataFrame()}
