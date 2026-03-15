import asyncio
import sys
from binance import AsyncClient
import logging
from config import config

# Fix: aiodns requires SelectorEventLoop on Windows
if sys.platform == "win32":
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except:
        pass

logger = logging.getLogger(__name__)

class BinanceClientManager:
    _client = None

    @classmethod
    async def get_client(cls):
        if cls._client is None:
            use_testnet = (config.TRADE_MODE.lower() == "paper_trading")
            cls._client = await AsyncClient.create(
                config.BINANCE_API_KEY, 
                config.BINANCE_API_SECRET, 
                testnet=use_testnet
            )
            logger.info(f"🌐 Binance Client initialized (Testnet={use_testnet})")
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close_connection()
            cls._client = None
            logger.info("🛑 Binance Client connection closed.")
