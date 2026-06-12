"""Trader control endpoints — start/stop/status/manual trigger for the trading loop."""

from datetime import date

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from apps.api.app.services.backtest_service import get_backtest_service
from apps.api.app.services.trader_service import get_trader_service
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/trader", tags=["trader"])


class WatchlistAddRequest(BaseModel):
    symbol: str


class BacktestRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=5)
    start_date: date
    end_date: date
    initial_capital: float = Field(default=100_000.0, gt=0)
    min_confidence: float = Field(default=0.55, ge=0.0, le=1.0)


@router.get("/status")
async def get_status() -> dict:
    return await get_trader_service().get_status()


@router.post("/start")
async def start_trader() -> dict:
    return await get_trader_service().start()


@router.post("/stop")
async def stop_trader() -> dict:
    return await get_trader_service().stop()


@router.post("/cycle/run")
async def trigger_cycle(background_tasks: BackgroundTasks) -> dict:
    """Manually fire one trading cycle right now (non-blocking)."""
    return await get_trader_service().trigger_cycle(background_tasks)


@router.get("/decisions")
async def get_decisions(limit: int = 20) -> list:
    return await get_trader_service().get_recent_decisions(limit=limit)


@router.get("/positions")
async def get_positions() -> list:
    return await get_trader_service().get_open_positions()


@router.get("/positions/closed")
async def get_closed_positions(limit: int = 50) -> list:
    return await get_trader_service().get_closed_positions(limit=limit)


@router.get("/reflections")
async def get_reflections(limit: int = 10) -> list:
    return await get_trader_service().get_recent_reflections(limit=limit)


# ── Historical backtest ───────────────────────────────────────────────────────

@router.post("/backtest")
async def start_backtest(body: BacktestRequest) -> dict:
    """Replay the trading agent over a historical date range (runs in background)."""
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    if body.start_date >= date.today():
        raise HTTPException(status_code=400, detail="start_date must be in the past")
    return await get_backtest_service().start(
        symbols=[s.upper().strip() for s in body.symbols],
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=body.initial_capital,
        min_confidence=body.min_confidence,
    )


@router.get("/backtest/{backtest_id}")
async def get_backtest(backtest_id: str) -> dict:
    """Poll backtest progress; returns the full result when completed."""
    state = await get_backtest_service().get(backtest_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Backtest not found or expired")
    return state


# ── Watchlist management ──────────────────────────────────────────────────────

@router.get("/watchlist")
async def get_watchlist() -> list[str]:
    return await get_trader_service().get_watchlist()


@router.post("/watchlist")
async def add_to_watchlist(body: WatchlistAddRequest) -> list[str]:
    symbol = body.symbol.upper().strip()
    if not symbol or not symbol.isalpha() or len(symbol) > 10:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    return await get_trader_service().add_to_watchlist(symbol)


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str) -> list[str]:
    return await get_trader_service().remove_from_watchlist(symbol.upper())
