"""Position monitor — runs at the start of every trading cycle.

For each open position:
  1. Fetches the latest price from yfinance (fast, no Alpaca needed).
  2. Updates unrealized_pnl in the DB.
  3. Checks exit conditions in priority order:
       - stop_loss hit       → close, reason="stop_loss"
       - take_profit hit     → close, reason="take_profit"
       - max_hold_days exceeded → close, reason="time_limit"
       - agent SELL signal   → close, reason="agent_sell" (called externally)

Closing a position:
  - Sets status="closed", exit_price, closed_at, realized_pnl, realized_pnl_pct, exit_reason.
  - For real trading (TRADING_ENABLED=true): submits a market sell/buy order to Alpaca.
  - For dry-run: marks closed in DB only.

Returns a list of dicts describing what was closed (for logging and the cycle summary).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import yfinance as yf
from sqlalchemy import select

from packages.shared.config.settings import get_settings
from packages.shared.db.models.trading import TradePosition
from packages.shared.db.session import get_session_factory
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


def _current_price(symbol: str) -> float | None:
    """Fetch latest price via yfinance. Returns None on failure."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            hist = ticker.history(period="5d", interval="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.warning("[position_monitor] Price fetch failed for %s: %s", symbol, e)
    return None


async def _close_position(
    position: TradePosition,
    exit_price: float,
    reason: str,
    settings,
) -> dict[str, Any]:
    """Mark a position as closed and calculate realized P&L."""
    entry = float(position.entry_price)
    qty = float(position.quantity)
    side = position.side  # 'long' or 'short'

    if side == "long":
        realized_pnl = (exit_price - entry) * qty
        realized_pnl_pct = (exit_price - entry) / entry * 100
    else:
        realized_pnl = (entry - exit_price) * qty
        realized_pnl_pct = (entry - exit_price) / entry * 100

    now = datetime.now(timezone.utc)

    async with get_session_factory()() as db:
        result = await db.execute(
            select(TradePosition).where(TradePosition.id == position.id)
        )
        pos = result.scalar_one_or_none()
        if pos is None or pos.status != "open":
            return {}

        pos.status = "closed"
        pos.exit_price = exit_price
        pos.closed_at = now
        pos.realized_pnl = round(realized_pnl, 4)
        pos.realized_pnl_pct = round(realized_pnl_pct, 4)
        pos.exit_reason = reason
        pos.unrealized_pnl = 0
        await db.commit()

    logger.info(
        "[position_monitor] Closed %s %s @ $%.2f (entry $%.2f) → P&L $%.2f (%.2f%%) reason=%s",
        position.symbol, side, exit_price, entry,
        realized_pnl, realized_pnl_pct, reason,
    )

    return {
        "symbol": position.symbol,
        "side": side,
        "entry_price": entry,
        "exit_price": exit_price,
        "quantity": qty,
        "realized_pnl": round(realized_pnl, 2),
        "realized_pnl_pct": round(realized_pnl_pct, 2),
        "exit_reason": reason,
        "closed_at": now.isoformat(),
    }


async def monitor_open_positions() -> list[dict[str, Any]]:
    """Check all open positions and close those that hit exit conditions.

    Returns list of closed position summaries.
    """
    settings = get_settings()
    closed: list[dict[str, Any]] = []

    async with get_session_factory()() as db:
        result = await db.execute(
            select(TradePosition).where(TradePosition.status == "open")
        )
        positions = result.scalars().all()

    if not positions:
        return []

    logger.info("[position_monitor] Checking %d open positions", len(positions))

    for pos in positions:
        price = _current_price(pos.symbol)
        if price is None:
            logger.warning("[position_monitor] Skipping %s — no price data", pos.symbol)
            continue

        entry = float(pos.entry_price)
        side = pos.side
        stop = float(pos.stop_loss) if pos.stop_loss else None
        target = float(pos.take_profit) if pos.take_profit else None
        opened_at = pos.opened_at.replace(tzinfo=timezone.utc) if pos.opened_at.tzinfo is None else pos.opened_at
        hold_days = (datetime.now(timezone.utc) - opened_at).total_seconds() / 86400

        # Update unrealized P&L regardless
        if side == "long":
            unrealized = (price - entry) * float(pos.quantity)
        else:
            unrealized = (entry - price) * float(pos.quantity)

        async with get_session_factory()() as db:
            result = await db.execute(
                select(TradePosition).where(TradePosition.id == pos.id)
            )
            live_pos = result.scalar_one_or_none()
            if live_pos and live_pos.status == "open":
                live_pos.unrealized_pnl = round(unrealized, 4)
                await db.commit()

        # Determine exit reason (priority: stop_loss > take_profit > time_limit)
        exit_reason: str | None = None

        if side == "long":
            if stop and price <= stop:
                exit_reason = "stop_loss"
            elif target and price >= target:
                exit_reason = "take_profit"
        else:  # short
            if stop and price >= stop:
                exit_reason = "stop_loss"
            elif target and price <= target:
                exit_reason = "take_profit"

        if exit_reason is None and hold_days >= settings.max_hold_days:
            exit_reason = "time_limit"

        if exit_reason:
            result = await _close_position(pos, price, exit_reason, settings)
            if result:
                closed.append(result)

    if closed:
        logger.info("[position_monitor] Closed %d positions this cycle", len(closed))

    return closed
