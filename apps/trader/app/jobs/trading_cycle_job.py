"""30-minute trading cycle job.

Iterates over the configured watchlist and invokes the trading graph for each
symbol. Respects market hours (NYSE 9:30-16:00 ET, Mon-Fri) and maintains one
active TradingSession per day.
"""

import asyncio
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import redis.asyncio as aioredis

_WATCHLIST_KEY = "trader:watchlist"

from packages.shared.config.settings import get_settings
from packages.shared.db.models.trading import TradingSession
from packages.shared.db.session import get_session_factory
from packages.shared.logging.logger import get_logger
from packages.trading_agent.orchestrator.trading_graph import get_trading_graph
from packages.trading_agent.tools.alpaca_trading import get_account_info
from apps.trader.app.jobs.position_monitor_job import monitor_open_positions

logger = get_logger(__name__)

_ET = ZoneInfo("America/New_York")
_DAILY_START_EQUITY_KEY = "trader:session:daily_start_equity"


def is_market_open() -> bool:
    """Return True if NYSE is currently open (9:30–16:00 ET, Mon–Fri)."""
    now_et = datetime.now(_ET)
    if now_et.weekday() >= 5:
        return False
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_et < market_close


async def _get_or_create_active_session(initial_equity: float, settings) -> str:
    """Return the active TradingSession ID for today, creating one if needed."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    async with get_session_factory()() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(TradingSession).where(
                TradingSession.status == "active",
                TradingSession.started_at >= today_start,
            )
        )
        session = result.scalar_one_or_none()

        if session is None:
            session = TradingSession(
                strategy_version=settings.trading_strategy_version,
                initial_capital=initial_equity,
                watchlist=settings.trading_watchlist,
                config_snapshot={
                    "trading_enabled": settings.trading_enabled,
                    "max_open_positions": settings.max_open_positions,
                    "max_position_size_usd": settings.max_position_size_usd,
                    "max_daily_drawdown_pct": settings.max_daily_drawdown_pct,
                    "min_decision_confidence": settings.min_decision_confidence,
                },
                status="active",
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            logger.info(
                "Created new TradingSession %s (equity=$%.2f)",
                session.id, float(session.initial_capital),
            )

        return str(session.id)


async def _cache_daily_start_equity(equity: float, settings) -> None:
    """Store start-of-day equity in Redis for circuit breaker calculation."""
    r = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Only set if not already set today (expires at midnight ET)
        existing = await r.get(_DAILY_START_EQUITY_KEY)
        if existing is None:
            # TTL: seconds until midnight ET
            now_et = datetime.now(_ET)
            midnight_et = now_et.replace(hour=23, minute=59, second=59, microsecond=0)
            ttl = int((midnight_et - now_et).total_seconds()) + 1
            await r.setex(_DAILY_START_EQUITY_KEY, ttl, str(equity))
            logger.info("Cached daily start equity: $%.2f (TTL=%ds)", equity, ttl)
    finally:
        await r.aclose()


async def run_trading_cycle(force: bool = False) -> None:
    """Main trading cycle — called by APScheduler every 30 minutes.

    Pass force=True to bypass the market-hours check (used for manual triggers).
    """
    if not force and not is_market_open():
        logger.info("Market closed — skipping trading cycle")
        return

    settings = get_settings()

    # Get account equity for session tracking
    try:
        account_json = get_account_info.invoke({"dummy": ""})
        account = json.loads(account_json)
        initial_equity = float(account.get("equity", 100_000.0))
    except Exception as e:
        logger.error("Failed to get account info: %s — using default equity", e)
        initial_equity = 100_000.0

    session_id = await _get_or_create_active_session(initial_equity, settings)
    await _cache_daily_start_equity(initial_equity, settings)

    # ── Step 1: Monitor open positions (close those hitting exit conditions) ──
    try:
        closed_positions = await monitor_open_positions()
        if closed_positions:
            logger.info(
                "Position monitor closed %d positions: %s",
                len(closed_positions),
                [f"{p['symbol']} {p['exit_reason']} P&L={p['realized_pnl_pct']:+.2f}%" for p in closed_positions],
            )
    except Exception as e:
        logger.error("Position monitor failed: %s", e)

    graph = get_trading_graph()

    # Read dynamic watchlist from Redis; fall back to settings default
    r = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await r.get(_WATCHLIST_KEY)
        watchlist: list[str] = json.loads(raw) if raw else list(settings.trading_watchlist)
    except Exception:
        watchlist = list(settings.trading_watchlist)
    finally:
        await r.aclose()

    logger.info(
        "Trading cycle starting: session=%s symbols=%s trading_enabled=%s",
        session_id, watchlist, settings.trading_enabled,
    )

    for symbol in watchlist:
        try:
            initial_state = {
                "session_id": session_id,
                "symbol": symbol,
                "watchlist": watchlist,
                "messages": [],
                "observation": None,
                "portfolio_state": None,
                "retrieved_memories": [],
                "memory_context_text": None,
                "trade_decision": None,
                "execution_result": None,
                "positions_to_reflect": [],
                "current_position_for_reflection": None,
                "original_decision_for_reflection": None,
                "reflection": None,
                "current_agent": "start",
                "errors": [],
                "market_regime": None,
                "trading_enabled": settings.trading_enabled,
                "circuit_breaker_active": False,
                "analysis_context": None,
            }
            await graph.ainvoke(initial_state)
            logger.info("Trading cycle completed for %s", symbol)
        except Exception as e:
            logger.error("Trading cycle failed for %s: %s", symbol, e)

        # Rate limiting between symbols
        await asyncio.sleep(2)

    logger.info("Trading cycle finished for all %d symbols", len(watchlist))
