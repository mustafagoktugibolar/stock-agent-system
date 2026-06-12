"""Portfolio state tool — combines account info, open positions, and circuit breaker status.

In dry-run mode (TRADING_ENABLED=false), reads the virtual portfolio from the DB
(positions with order_id IS NULL) using a direct psycopg2 sync connection so this
@tool (which must be synchronous) never needs to bridge into an asyncio event loop.
"""

import json

import psycopg2
import psycopg2.extras
import redis
from langchain_core.tools import tool

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.trading_agent.tools.alpaca_trading import get_account_info, get_open_positions

logger = get_logger(__name__)

_DAILY_START_EQUITY_KEY = "trader:session:daily_start_equity"


def _get_virtual_portfolio_sync() -> dict:
    """Build portfolio state from virtual positions using a sync psycopg2 connection."""
    settings = get_settings()

    # Build a sync DSN from the async URL (strip +asyncpg if present)
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    virtual_positions = []
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT symbol, quantity, entry_price, unrealized_pnl, side
                FROM trade_positions
                WHERE order_id IS NULL AND status = 'open'
                """
            )
            virtual_positions = cur.fetchall()
        conn.close()
    except Exception as e:
        logger.warning("[portfolio_state] DB query failed: %s — returning empty portfolio", e)

    committed_capital = sum(
        float(p["quantity"]) * float(p["entry_price"])
        for p in virtual_positions
    )
    virtual_cash = max(0.0, settings.virtual_starting_capital - committed_capital)
    total_unrealized = sum(
        float(p["unrealized_pnl"]) if p["unrealized_pnl"] else 0.0
        for p in virtual_positions
    )
    open_symbols = [p["symbol"] for p in virtual_positions]

    positions_list = [
        {
            "symbol": p["symbol"],
            "qty": float(p["quantity"]),
            "avg_entry_price": float(p["entry_price"]),
            "current_price": float(p["entry_price"]),
            "unrealized_pl": float(p["unrealized_pnl"]) if p["unrealized_pnl"] else 0.0,
            "unrealized_plpc": 0.0,
            "side": p["side"],
            "virtual": True,
        }
        for p in virtual_positions
    ]

    return {
        "current_equity": settings.virtual_starting_capital + total_unrealized,
        "cash": virtual_cash,
        "buying_power": virtual_cash,
        "total_open_positions": len(virtual_positions),
        "open_position_symbols": open_symbols,
        "positions": positions_list,
        "total_unrealized_pnl": total_unrealized,
        "daily_start_equity": settings.virtual_starting_capital,
        "daily_pnl_pct": round(
            total_unrealized / settings.virtual_starting_capital * 100.0, 4
        ) if settings.virtual_starting_capital > 0 else 0.0,
        "circuit_breaker_active": False,
        "max_daily_drawdown_pct": settings.max_daily_drawdown_pct,
        "mode": "simulated",
    }


def _get_daily_start_equity(current_equity: float) -> float:
    """Read daily start equity from Redis using sync redis client."""
    settings = get_settings()
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        val = r.get(_DAILY_START_EQUITY_KEY)
        r.close()
        return float(val) if val else current_equity
    except Exception:
        return current_equity


@tool
def get_portfolio_state(dummy: str = "") -> str:
    """Get combined portfolio state: account summary, open positions, and circuit breaker status.

    In dry-run mode returns the simulated virtual portfolio tracked in the DB.
    In live mode reads from Alpaca paper account.
    """
    settings = get_settings()

    if not settings.trading_enabled:
        return json.dumps(_get_virtual_portfolio_sync())

    # ── Live mode: read from Alpaca ───────────────────────────────────────────
    account_json = get_account_info.invoke({"dummy": ""})
    account = json.loads(account_json)
    if "error" in account:
        return json.dumps({"error": f"account fetch failed: {account['error']}"})

    positions_json = get_open_positions.invoke({"dummy": ""})
    positions_data = json.loads(positions_json)
    if isinstance(positions_data, dict) and "error" in positions_data:
        positions_data = []

    current_equity = account.get("equity", 0.0)
    total_unrealized_pnl = sum(p.get("unrealized_pl", 0.0) or 0.0 for p in positions_data)
    open_position_symbols = [p["symbol"] for p in positions_data]

    start_equity = _get_daily_start_equity(current_equity)
    daily_pnl_pct = (
        (current_equity - start_equity) / start_equity * 100.0
        if start_equity > 0 else 0.0
    )
    circuit_breaker_active = daily_pnl_pct < -settings.max_daily_drawdown_pct

    return json.dumps({
        "current_equity": current_equity,
        "cash": account.get("cash", 0.0),
        "buying_power": account.get("buying_power", 0.0),
        "total_open_positions": len(positions_data),
        "open_position_symbols": open_position_symbols,
        "positions": positions_data,
        "total_unrealized_pnl": total_unrealized_pnl,
        "daily_start_equity": start_equity,
        "daily_pnl_pct": round(daily_pnl_pct, 4),
        "circuit_breaker_active": circuit_breaker_active,
        "max_daily_drawdown_pct": settings.max_daily_drawdown_pct,
        "mode": "live",
    })
