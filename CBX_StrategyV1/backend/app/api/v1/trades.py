from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.api.dependencies import get_current_user, get_db, get_redis
from app.models.trade import Trade
from app.schemas.trade import TradeRead

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def list_trades(
    symbol_id: Optional[UUID] = None,
    side: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Trade).order_by(desc(Trade.entry_time))
    
    if symbol_id:
        query = query.where(Trade.symbol_id == symbol_id)
    if side:
        query = query.where(Trade.side == side)
    if status:
        query = query.where(Trade.status == status)
        
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    # Get paginated results
    result = await db.execute(query.limit(limit).offset(offset))
    trades = result.scalars().all()
    
    return {
        "success": True,
        "data": {
            "trades": trades,
            "total": total_count,
            "page_info": {
                "limit": limit,
                "offset": offset
            }
        }
    }

@router.get("/open", response_model=List[TradeRead])
async def get_open_trades(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    query = select(Trade).where(Trade.status == "OPEN").order_by(desc(Trade.entry_time))
    result = await db.execute(query)
    trades = result.scalars().all()
    
    # Calculate unrealized PnL for each trade
    for t in trades:
        # Get current price from Redis
        price_key = f"price:BTCUSDC" # Mock symbol lookup
        current_price_raw = await redis.get(price_key)
        if current_price_raw:
            current_price = Decimal(current_price_raw.decode())
            # Simple unrealized PnL calculation
            if t.side == "LONG":
                t.unrealized_pnl_r = (current_price - t.entry_price) / (t.entry_price * Decimal("0.01")) # Mock R calculation
            else:
                t.unrealized_pnl_r = (t.entry_price - current_price) / (t.entry_price * Decimal("0.01"))
        else:
            t.unrealized_pnl_r = Decimal("0")
            
    return trades

@router.get("/{trade_id}", response_model=TradeRead)
async def get_trade_detail(
    trade_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Trade).where(Trade.trade_id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade

@router.post("/{trade_id}/close")
async def force_close_trade(
    trade_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # This would call order_executor.place_market_order() in a real scenario
    result = await db.execute(select(Trade).where(Trade.trade_id == trade_id))
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "OPEN":
        raise HTTPException(status_code=400, detail="Trade is already closed")
        
    # Mocking close
    trade.status = "CLOSED"
    trade.exit_time = datetime.utcnow()
    # In reality, we'd wait for execution result
    
    await db.commit()
    return {"success": True, "message": f"Trade {trade_id} closed manually."}
