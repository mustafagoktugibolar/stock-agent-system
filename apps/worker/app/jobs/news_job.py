"""Periodic job: pre-warm the news cache for a watchlist of symbols."""

import asyncio

import redis.asyncio as aioredis

from packages.agent_core.tools.news_fetcher import fetch_recent_news
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

DEFAULT_WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY"]
NEWS_CACHE_TTL = 600  # 10 minutes


async def fetch_news_for_watchlist(
    redis_client: aioredis.Redis,
    watchlist: list[str] = DEFAULT_WATCHLIST,
) -> None:
    """Fetch and cache recent news for each symbol in the watchlist."""
    logger.info("News job started — %d symbols", len(watchlist))
    success, failed = 0, 0

    for symbol in watchlist:
        try:
            news_json = fetch_recent_news.invoke({"symbol": symbol, "max_articles": 10})
            await redis_client.setex(f"news:{symbol}", NEWS_CACHE_TTL, news_json)
            success += 1
            logger.debug("News cached for %s", symbol)
        except Exception as e:
            failed += 1
            logger.error("News fetch failed for %s: %s", symbol, e)

        await asyncio.sleep(1)  # gentle rate limiting

    logger.info("News job done — success=%d failed=%d", success, failed)
