from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import asyncio
import logging

from app.api.dependencies import get_current_user, get_db
from app.models.run import ResearchRun
from app.schemas.run import ResearchRunRead, BacktestConfigSchema
from app.backtest.engine import BacktestEngine, BacktestConfig

router = APIRouter()
logger = logging.getLogger(__name__)

async def _run_backtest_task(run_id: UUID, config: BacktestConfig, db_factory):
    """Background task to run backtest and handle failures."""
    async with db_factory() as db:
        try:
            # 1. Get the run record
            result = await db.execute(select(ResearchRun).where(ResearchRun.run_id == run_id))
            run = result.scalar_one_or_none()
            if not run:
                logger.error(f"Run {run_id} not found in background task")
                return

            # 2. Execute backtest
            engine = BacktestEngine(db_factory)
            # engine.run() is expected to update DB during/after run
            await engine.run(config, run_id=run_id)
            
            logger.info(f"Backtest run {run_id} completed successfully")

        except Exception as e:
            logger.error(f"Backtest run {run_id} failed: {str(e)}", exc_info=True)
            # Ensure the fail status is persisted
            try:
                # Refresh run object in this session
                result = await db.execute(select(ResearchRun).where(ResearchRun.run_id == run_id))
                run = result.scalar_one_or_none()
                if run:
                    run.status = "FAILED"
                    run.run_end = datetime.utcnow()
                    run.notes = f"Error: {str(e)}"
                    await db.commit()
            except Exception as inner_e:
                logger.critical(f"Critical error updating FAILED status for run {run_id}: {str(inner_e)}")

@router.get("/", response_model=List[ResearchRunRead])
async def list_runs(
    symbol_id: Optional[UUID] = None,
    mode: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(ResearchRun).order_by(desc(ResearchRun.run_start))
    if symbol_id:
        query = query.where(ResearchRun.symbol_id == symbol_id)
    if mode:
        query = query.where(ResearchRun.mode == mode)
    if status:
        query = query.where(ResearchRun.status == status)
        
    result = await db.execute(query.limit(limit))
    return result.scalars().all()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def start_backtest_run(
    config_in: BacktestConfigSchema,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Create ResearchRun record
    run_id = uuid4()
    new_run = ResearchRun(
        run_id=run_id,
        run_name=config_in.run_name,
        symbol_id=config_in.symbol_id,
        strategy_config_id=config_in.strategy_config_id,
        mode="BACKTEST",
        status="RUNNING",
        entry_model=config_in.entry_model,
        side_filter=config_in.side_filter,
        data_start=config_in.data_start,
        data_end=config_in.data_end,
        run_start=datetime.utcnow()
    )
    db.add(new_run)
    await db.commit()
    
    # 2. Prepare BacktestConfig
    engine_config = BacktestConfig(
        symbol_id=config_in.symbol_id,
        strategy_config_id=config_in.strategy_config_id,
        start_date=config_in.data_start,
        end_date=config_in.data_end,
        initial_equity=config_in.initial_equity
    )

    # 3. Schedule background task
    # We pass a callable that returns a new DB session for the background task
    from app.database import AsyncSessionLocal
    background_tasks.add_task(_run_backtest_task, run_id, engine_config, AsyncSessionLocal)

    return {
        "success": True,
        "run_id": run_id,
        "status": "RUNNING",
        "message": "Backtest started successfully in background"
    }

@router.get("/{run_id}", response_model=ResearchRunRead)
async def get_run_detail(
    run_id: UUID,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ResearchRun).where(ResearchRun.run_id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
