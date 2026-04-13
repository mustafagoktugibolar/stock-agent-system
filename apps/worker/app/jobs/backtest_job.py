"""Periodic job: validate past recommendations against actual price movements."""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis.asyncio as aioredis

from packages.agent_core.tools.market_data import fetch_ohlcv
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_HORIZONS_DAYS = {"short_term": 5, "medium_term": 20, "long_term": 60}


def _evaluate_recommendation(
    recommendation: str,
    entry_price: float,
    current_price: float,
) -> dict:
    """Determine if a recommendation was correct based on subsequent price movement."""
    pct_change = (current_price - entry_price) / entry_price * 100
    correct = (
        (recommendation == "BUY" and pct_change > 2)
        or (recommendation == "SELL" and pct_change < -2)
        or (recommendation == "HOLD" and abs(pct_change) <= 5)
    )
    return {
        "entry_price": entry_price,
        "current_price": current_price,
        "pct_change": round(pct_change, 2),
        "correct": correct,
    }


async def run_backtest(
    redis_client: aioredis.Redis,
    symbol: str,
    recommendation: str,
    entry_price: float,
    horizon: str = "medium_term",
    analysis_id: Optional[str] = None,
) -> dict:
    """Evaluate a past recommendation against real price data.

    Fetches the most recent closing price for the symbol and computes
    whether the recommendation was directionally correct.
    """
    logger.info(
        "Backtest for %s — rec=%s entry=%.2f horizon=%s",
        symbol,
        recommendation,
        entry_price,
        horizon,
    )
    try:
        ohlcv_json = fetch_ohlcv.invoke({"symbol": symbol, "period": "1mo", "interval": "1d"})
        data = json.loads(ohlcv_json)
        bars = data.get("bars", [])
        if not bars:
            return {"error": "No price data available for backtest"}

        days = _HORIZONS_DAYS.get(horizon, 20)
        target_idx = min(days, len(bars) - 1)
        current_price = float(bars[target_idx]["close"])

        result = _evaluate_recommendation(recommendation, entry_price, current_price)
        result.update(
            {
                "symbol": symbol,
                "recommendation": recommendation,
                "horizon": horizon,
                "analysis_id": analysis_id,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        if analysis_id:
            await redis_client.setex(
                f"backtest:{analysis_id}",
                86400 * 7,  # 7-day retention
                json.dumps(result),
            )

        logger.info(
            "Backtest result for %s: pct_change=%.2f%% correct=%s",
            symbol,
            result["pct_change"],
            result["correct"],
        )
        return result

    except Exception as e:
        logger.error("Backtest failed for %s: %s", symbol, e)
        return {"error": str(e), "symbol": symbol}
