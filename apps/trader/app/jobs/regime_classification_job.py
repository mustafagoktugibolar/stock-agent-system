"""Daily market regime classification job — runs at 9:25 AM ET before market open.

Fetches SPY OHLCV data, classifies the current market regime using the same
deterministic ruleset as the market observer agent, and caches the result in
Redis (TTL 8 hours) for use by the trading cycle.
"""

import json

import redis.asyncio as aioredis

from packages.analysis_agent.tools.indicators import calculate_technical_indicators
from packages.analysis_agent.tools.market_data import fetch_ohlcv
from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_REGIME_CACHE_KEY = "trader:market_regime:SPY"
_REGIME_TTL = 28800  # 8 hours


def _classify_regime(adx: float | None, change_24h: float | None, volatility: float | None) -> str:
    vol = volatility or 0.0
    adx_val = adx or 0.0
    change = change_24h or 0.0

    if vol > 40.0:
        return "high_volatility"
    if adx_val > 25.0 and change > 0:
        return "trending_bull"
    if adx_val > 25.0 and change < 0:
        return "trending_bear"
    return "ranging"


async def run_regime_classification() -> None:
    """Classify SPY market regime and cache result in Redis."""
    settings = get_settings()

    try:
        ohlcv_json = fetch_ohlcv.invoke({"symbol": "SPY", "period": "3mo", "interval": "1d"})
        indicators_json = calculate_technical_indicators.invoke({"ohlcv_json": ohlcv_json})
        indicators = json.loads(indicators_json)

        bars = json.loads(ohlcv_json).get("bars", [])
        change_24h: float | None = None
        if len(bars) >= 2:
            prev = float(bars[-2].get("close", 0))
            curr = float(bars[-1].get("close", 0))
            if prev > 0:
                change_24h = (curr - prev) / prev * 100

        adx = indicators.get("adx")
        volatility = indicators.get("annualized_volatility")

        regime = _classify_regime(
            adx=float(adx) if adx is not None else None,
            change_24h=change_24h,
            volatility=float(volatility) if volatility is not None else None,
        )

        r = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await r.setex(_REGIME_CACHE_KEY, _REGIME_TTL, regime)
            logger.info("Market regime classified as: %s (SPY ADX=%.1f)", regime, adx or 0.0)
        finally:
            await r.aclose()

    except Exception as e:
        logger.error("Regime classification failed: %s", e)
