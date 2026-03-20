from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.api.dependencies import get_current_user, get_db
from app.models.session import SessionState, EquitySnapshot

router = APIRouter()

@router.get("/session", response_model=List[Dict[str, Any]])
async def list_session_states(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SessionState).order_by(SessionState.symbol_id))
    return result.scalars().all()

@router.get("/equity", response_model=List[Dict[str, Any]])
async def get_equity_curve(
    run_id: Optional[UUID] = None,
    limit: int = 100,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(EquitySnapshot).order_by(EquitySnapshot.time)
    if run_id:
        query = query.where(EquitySnapshot.run_id == run_id)
    
    result = await db.execute(query.limit(limit))
    return result.scalars().all()

@router.post("/reset-halt")
async def reset_halt(
    body: Dict[str, Optional[UUID]] = None,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    symbol_id = body.get("symbol_id") if body else None
    
    stmt = update(SessionState).values(
        trading_halted=False,
        consecutive_failures=0,
        halt_reason=None,
        halt_at=None
    )
    
    if symbol_id:
        stmt = stmt.where(SessionState.symbol_id == symbol_id)
        
    result = await db.execute(stmt)
    await db.commit()
    
    return {
        "success": True, 
        "reset_count": result.rowcount,
        "message": f"Halt reset for {'symbol ' + str(symbol_id) if symbol_id else 'all symbols'}."
    }
