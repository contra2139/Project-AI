import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT symbol FROM symbol_registry"))
            symbols = res.fetchall()
            print(f"Symbols in registry: {symbols}")
            
            for table in ["ohlcv_15m", "ohlcv_1h"]:
                res = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                print(f"Rows in {table}: {res.scalar()}")
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    asyncio.run(check())
