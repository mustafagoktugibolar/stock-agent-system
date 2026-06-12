"""Trader lifecycle service — manages APScheduler within the FastAPI process.

The scheduler is not started automatically; it is started/stopped via API endpoints
from the frontend trading dashboard.

Watchlist is stored in Redis (key: trader:watchlist) as a JSON list.
Falls back to settings.trading_watchlist if the Redis key doesn't exist.
"""

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import desc, select, text

from apps.trader.app.jobs.reflection_job import run_reflection
from apps.trader.app.jobs.regime_classification_job import run_regime_classification
from apps.trader.app.jobs.trading_cycle_job import run_trading_cycle
from packages.shared.config.settings import get_settings
from packages.shared.db.models.trading import TradeDecision, TradePosition, TradeReflection
from packages.shared.db.session import get_session_factory
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


_WATCHLIST_KEY = "trader:watchlist"


class TraderService:
    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    def is_running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running

    # ── Watchlist management (Redis-backed) ──────────────────────────────────

    async def _redis(self) -> aioredis.Redis:
        settings = get_settings()
        return aioredis.Redis.from_url(settings.redis_url, decode_responses=True)

    async def get_watchlist(self) -> list[str]:
        r = await self._redis()
        try:
            raw = await r.get(_WATCHLIST_KEY)
            if raw:
                return json.loads(raw)
            return list(get_settings().trading_watchlist)
        finally:
            await r.aclose()

    async def add_to_watchlist(self, symbol: str) -> list[str]:
        symbol = symbol.upper().strip()
        watchlist = await self.get_watchlist()
        if symbol not in watchlist:
            watchlist.append(symbol)
            r = await self._redis()
            try:
                await r.set(_WATCHLIST_KEY, json.dumps(watchlist))
            finally:
                await r.aclose()
        return watchlist

    async def remove_from_watchlist(self, symbol: str) -> list[str]:
        symbol = symbol.upper().strip()
        watchlist = await self.get_watchlist()
        watchlist = [s for s in watchlist if s != symbol]
        r = await self._redis()
        try:
            await r.set(_WATCHLIST_KEY, json.dumps(watchlist))
        finally:
            await r.aclose()
        return watchlist

    async def start(self) -> dict[str, Any]:
        if self.is_running():
            return {"status": "already_running", "message": "Trader is already running"}

        self._scheduler = AsyncIOScheduler(timezone="America/New_York")

        self._scheduler.add_job(
            run_trading_cycle,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour="9-15",
                minute="0,30",
                timezone="America/New_York",
            ),
            id="trading_cycle",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=120,
        )
        self._scheduler.add_job(
            run_reflection,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=16,
                minute=15,
                timezone="America/New_York",
            ),
            id="reflection_job",
            max_instances=1,
            coalesce=True,
        )
        self._scheduler.add_job(
            run_regime_classification,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=9,
                minute=25,
                timezone="America/New_York",
            ),
            id="regime_classification",
            max_instances=1,
            coalesce=True,
        )

        self._scheduler.start()
        logger.info("Trader scheduler started via dashboard")
        return {"status": "started", "message": "Trader started successfully"}

    async def stop(self) -> dict[str, Any]:
        if not self.is_running():
            return {"status": "not_running", "message": "Trader is not running"}

        self._scheduler.shutdown(wait=False)
        self._scheduler = None
        logger.info("Trader scheduler stopped via dashboard")
        return {"status": "stopped", "message": "Trader stopped successfully"}

    async def trigger_cycle(self, background_tasks=None) -> dict[str, Any]:
        """Manually fire one trading cycle immediately, bypassing market hours."""
        logger.info("Manual cycle trigger — force=True, market hours bypassed")
        if background_tasks is not None:
            background_tasks.add_task(run_trading_cycle, force=True)
        else:
            asyncio.create_task(run_trading_cycle(force=True))
        return {"status": "triggered", "message": "Trading cycle started in background"}

    async def get_status(self) -> dict[str, Any]:
        settings = get_settings()
        jobs: list[dict] = []
        if self._scheduler:
            for job in self._scheduler.get_jobs():
                next_run = job.next_run_time
                jobs.append({
                    "id": job.id,
                    "next_run": next_run.isoformat() if next_run else None,
                })

        virtual_portfolio: dict | None = None
        if not settings.trading_enabled:
            virtual_portfolio = await self._get_virtual_portfolio_summary()

        watchlist = await self.get_watchlist()

        return {
            "running": self.is_running(),
            "trading_enabled": settings.trading_enabled,
            "watchlist": watchlist,
            "max_open_positions": settings.max_open_positions,
            "min_decision_confidence": settings.min_decision_confidence,
            "max_position_size_usd": settings.max_position_size_usd,
            "virtual_starting_capital": settings.virtual_starting_capital,
            "virtual_portfolio": virtual_portfolio,
            "jobs": jobs,
        }

    async def _get_virtual_portfolio_summary(self) -> dict:
        """Compute virtual portfolio balance from open virtual positions in DB."""
        from packages.shared.db.models.trading import TradePosition  # noqa: PLC0415
        from packages.shared.db.session import get_session_factory    # noqa: PLC0415
        settings = get_settings()

        async with get_session_factory()() as db:
            result = await db.execute(
                select(TradePosition).where(
                    TradePosition.order_id.is_(None),
                    TradePosition.status == "open",
                )
            )
            positions = result.scalars().all()

        committed = sum(float(p.quantity) * float(p.entry_price) for p in positions)
        available_cash = max(0.0, settings.virtual_starting_capital - committed)
        total_unrealized = sum(
            float(p.unrealized_pnl) if p.unrealized_pnl else 0.0
            for p in positions
        )
        return {
            "starting_capital": settings.virtual_starting_capital,
            "committed_capital": round(committed, 2),
            "available_cash": round(available_cash, 2),
            "open_positions": len(positions),
            "total_unrealized_pnl": round(total_unrealized, 2),
            "equity": round(settings.virtual_starting_capital + total_unrealized, 2),
        }

    async def get_recent_decisions(self, limit: int = 20) -> list[dict]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(TradeDecision)
                .order_by(desc(TradeDecision.decided_at))
                .limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(d.id),
                    "symbol": d.symbol,
                    "action": d.action,
                    "confidence": float(d.confidence),
                    "market_regime": d.market_regime,
                    "reasoning": (d.reasoning or "")[:200],
                    "decided_at": d.decided_at.isoformat(),
                }
                for d in rows
            ]

    async def get_open_positions(self) -> list[dict]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(TradePosition)
                .where(TradePosition.status == "open")
                .order_by(desc(TradePosition.opened_at))
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(p.id),
                    "symbol": p.symbol,
                    "side": p.side,
                    "quantity": float(p.quantity),
                    "entry_price": float(p.entry_price),
                    "stop_loss": float(p.stop_loss) if p.stop_loss else None,
                    "take_profit": float(p.take_profit) if p.take_profit else None,
                    "unrealized_pnl": float(p.unrealized_pnl) if p.unrealized_pnl else None,
                    "opened_at": p.opened_at.isoformat(),
                }
                for p in rows
            ]

    async def get_closed_positions(self, limit: int = 50) -> list[dict]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(TradePosition)
                .where(TradePosition.status == "closed")
                .order_by(desc(TradePosition.closed_at))
                .limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(p.id),
                    "symbol": p.symbol,
                    "side": p.side,
                    "quantity": float(p.quantity),
                    "entry_price": float(p.entry_price),
                    "exit_price": float(p.exit_price) if p.exit_price else None,
                    "realized_pnl": float(p.realized_pnl) if p.realized_pnl else None,
                    "realized_pnl_pct": float(p.realized_pnl_pct) if p.realized_pnl_pct else None,
                    "exit_reason": p.exit_reason,
                    "opened_at": p.opened_at.isoformat(),
                    "closed_at": p.closed_at.isoformat() if p.closed_at else None,
                }
                for p in rows
            ]

    async def get_recent_reflections(self, limit: int = 10) -> list[dict]:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(TradeReflection)
                .order_by(desc(TradeReflection.reflected_at))
                .limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "symbol": r.symbol,
                    "outcome": r.outcome,
                    "pnl_pct": float(r.pnl_pct) if r.pnl_pct else None,
                    "lessons_learned": r.lessons_learned,
                    "memory_stored": r.memory_stored,
                    "reflected_at": r.reflected_at.isoformat(),
                }
                for r in rows
            ]


_instance: TraderService | None = None


def get_trader_service() -> TraderService:
    global _instance
    if _instance is None:
        _instance = TraderService()
    return _instance
