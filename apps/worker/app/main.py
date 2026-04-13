"""Worker entry point — runs periodic background jobs."""

import asyncio

import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

from apps.worker.app.jobs.news_job import fetch_news_for_watchlist  # noqa: E402
from packages.shared.config.settings import get_settings  # noqa: E402
from packages.shared.logging.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

NEWS_JOB_INTERVAL = 600  # run every 10 minutes


async def run_forever() -> None:
    settings = get_settings()
    redis_client = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Worker started — news job interval: %ds", NEWS_JOB_INTERVAL)

    try:
        while True:
            await fetch_news_for_watchlist(redis_client)
            logger.info("Sleeping %ds until next news job run", NEWS_JOB_INTERVAL)
            await asyncio.sleep(NEWS_JOB_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Worker shutdown requested")
    finally:
        await redis_client.aclose()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(run_forever())
