from fastapi import APIRouter
from app.api.v1 import auth, symbols, settings, signals, trades, risk, runs

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(symbols.router, prefix="/symbols", tags=["Symbols"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(signals.router, prefix="/signals", tags=["Signals"])
api_router.include_router(trades.router, prefix="/trades", tags=["Trades"])
api_router.include_router(risk.router, prefix="/risk", tags=["Risk"])
api_router.include_router(runs.router, prefix="/runs", tags=["Research Runs"])
