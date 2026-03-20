from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.api.dependencies import get_current_user, get_db
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig, StrategyVersionHistory
from app.schemas.symbol import SymbolRegistryRead, SymbolRegistryCreate, SymbolStrategyConfigRead, SymbolStrategyConfigCreate

router = APIRouter()

@router.get("/", response_model=List[SymbolRegistryRead])
async def list_symbols(
    is_active: Optional[bool] = None,
    is_in_universe: Optional[bool] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(SymbolRegistry)
    if is_active is not None:
        query = query.where(SymbolRegistry.is_active == is_active)
    if is_in_universe is not None:
        query = query.where(SymbolRegistry.is_in_universe == is_in_universe)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=SymbolRegistryRead)
async def create_symbol(
    symbol_data: SymbolRegistryCreate,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if exists
    existing = await db.execute(select(SymbolRegistry).where(SymbolRegistry.symbol == symbol_data.symbol))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Symbol already registered")
    
    new_symbol = SymbolRegistry(
        symbol=symbol_data.symbol,
        exchange=symbol_data.exchange,
        is_active=symbol_data.is_active,
        is_in_universe=symbol_data.is_in_universe,
        base_asset=symbol_data.symbol.replace("USDC", "").replace("USDT", ""), # Simple parse
        quote_asset="USDC" if "USDC" in symbol_data.symbol else "USDT",
        contract_type="PERP"
    )
    db.add(new_symbol)
    await db.commit()
    await db.refresh(new_symbol)
    return new_symbol

@router.get("/{symbol_id}", response_model=SymbolRegistryRead)
async def get_symbol(
    symbol_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SymbolRegistry).where(SymbolRegistry.symbol_id == symbol_id))
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return symbol

@router.get("/{symbol_id}/config", response_model=List[SymbolStrategyConfigRead])
async def get_symbol_config_history(
    symbol_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SymbolStrategyConfig)
        .where(SymbolStrategyConfig.symbol_id == symbol_id)
        .order_by(SymbolStrategyConfig.version.desc())
    )
    return result.scalars().all()

@router.put("/{symbol_id}/config", response_model=SymbolStrategyConfigRead)
async def update_symbol_config(
    symbol_id: UUID,
    config_data: SymbolStrategyConfigCreate,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Get current version
    result = await db.execute(
        select(SymbolStrategyConfig)
        .where(SymbolStrategyConfig.symbol_id == symbol_id, SymbolStrategyConfig.is_current == True)
    )
    current_config = result.scalar_one_or_none()
    
    new_version = 1
    if current_config:
        new_version = current_config.version + 1
        # Set old to not current
        current_config.is_current = False
    
    # 2. Create new config version
    new_config = SymbolStrategyConfig(
        symbol_id=symbol_id,
        version=new_version,
        is_current=True,
        created_by=current_user,
        **config_data.model_dump()
    )
    db.add(new_config)
    
    # 3. Log to history
    history = StrategyVersionHistory(
        symbol_id=symbol_id,
        from_version=current_config.version if current_config else 0,
        to_version=new_version,
        changed_by=current_user,
        params_diff=config_data.model_dump(), # Simple dump for now
        reason="Manual update via API"
    )
    db.add(history)
    
    await db.commit()
    await db.refresh(new_config)
    return new_config
