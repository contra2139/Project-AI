from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID

from app.api.dependencies import get_current_user, get_db, get_redis
from app.models.events import BreakoutEvent # Assuming signals are derived from breakouts or similar
from app.schemas.signal import SignalSummary, SignalNotificationDetailed

router = APIRouter()

@router.get("/", response_model=List[SignalSummary])
async def list_signals(
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    limit: int = 20,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    # This endpoint ideally merges active signals from Redis and history from DB
    # For now, we'll fetch from DB (BreakoutEvents as proxy for signals)
    query = select(BreakoutEvent).order_by(desc(BreakoutEvent.time)).limit(limit)
    
    # In a real scenario, we would filter by symbol/side and join with other tables
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Mock return for now as the Signal model might be separate or derived
    return [
        {
            "signal_id": e.breakout_id,
            "symbol": "BTCUSDC", # Should come from relation
            "side": e.side,
            "time": e.time,
            "price": e.price,
            "quality_score": 85.0 # Mock
        } for e in events
    ]

@router.get("/{signal_id}", response_model=SignalNotificationDetailed)
async def get_signal_detail(
    signal_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch detailed signal with event chain
    result = await db.execute(select(BreakoutEvent).where(BreakoutEvent.breakout_id == signal_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Signal not found")
        
    return {
        "signal_id": event.breakout_id,
        "symbol_id": event.symbol_id,
        "time": event.time,
        "side": event.side,
        "entry_price": event.price,
        "stop_loss": event.price * 0.98, # Mock
        "take_profit": event.price * 1.05, # Mock
        "ai_score_v1": 78.5,
        "quality_score": 82.0,
        "compression_id": event.compression_id,
        "breakout_id": event.breakout_id,
        "expansion_id": None
    }
