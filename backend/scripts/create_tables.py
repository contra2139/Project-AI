import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
import uuid
from decimal import Decimal
from datetime import datetime

# Thêm 'backend' vào sys.path để 'import app' hoạt động bên trong các models
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
backend_dir = os.path.join(root, 'backend')
sys.path.insert(0, backend_dir)
sys.path.insert(0, root)

from app.database import Base
from app.models.run import ResearchRun
from app.models.trade import Trade
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig
import app.models.session 
import app.models.events
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///e:/Agent_AI_Antigravity/CBX_StrategyV1/test.db"

async def create_tables():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Drop only what we want to recreate if it was messy
        # await conn.run_sync(Base.metadata.drop_all) 
        await conn.run_sync(Base.metadata.create_all)
    
    print("Tables created successfully.")

    # Re-insert Registry and Configs since create_all doesn't insert data
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # BTC
        btc_id = UUID('bd1d0c1d-8564-40cb-a6d0-89376ebfa96a')
        res = await session.get(SymbolRegistry, btc_id)
        if not res:
            session.add(SymbolRegistry(symbol_id=btc_id, symbol="BTCUSDC", base_asset="BTC", quote_asset="USDC", exchange="BINANCE", contract_type="PERP"))
        
        # BNB
        bnb_id = UUID('bd2d0c2d-8564-40cb-a6d0-89376ebfa96b')
        res = await session.get(SymbolRegistry, bnb_id)
        if not res:
            session.add(SymbolRegistry(symbol_id=bnb_id, symbol="BNBUSDC", base_asset="BNB", quote_asset="USDC", exchange="BINANCE", contract_type="PERP"))

        # SOL
        sol_id = UUID('bd3d0c3d-8564-40cb-a6d0-89376ebfa96c')
        res = await session.get(SymbolRegistry, sol_id)
        if not res:
            session.add(SymbolRegistry(symbol_id=sol_id, symbol="SOLUSDC", base_asset="SOL", quote_asset="USDC", exchange="BINANCE", contract_type="PERP"))

        await session.commit()
    
    print("Registry done.")

if __name__ == "__main__":
    from uuid import UUID
    asyncio.run(create_tables())
