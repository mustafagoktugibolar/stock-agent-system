"""Trader app entry point — APScheduler-based autonomous trading loop.

Three jobs:
  - trading_cycle:        every 30 min, Mon-Fri 9:00-15:30 ET
  - reflection:           daily at 4:15 PM ET (market close + 15 min buffer)
  - regime_classification: daily at 9:25 AM ET (5 min before open)

TRADING_ENABLED=false by default — the system reasons and logs decisions in
dry-run mode without placing real paper orders.
"""

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

from apps.trader.app.jobs.reflection_job import run_reflection              # noqa: E402
from apps.trader.app.jobs.regime_classification_job import run_regime_classification  # noqa: E402
from apps.trader.app.jobs.trading_cycle_job import run_trading_cycle        # noqa: E402
from packages.shared.config.settings import get_settings                    # noqa: E402
from packages.shared.db.session import create_tables, dispose_engine        # noqa: E402
from packages.shared.logging.logger import get_logger                       # noqa: E402

logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()

    logger.info(
        "Trader starting — trading_enabled=%s watchlist=%s",
        settings.trading_enabled,
        settings.trading_watchlist,
    )

    # Ensure all tables exist (idempotent, also creates pgvector extension + HNSW index)
    await create_tables()

    scheduler = AsyncIOScheduler(timezone="America/New_York")

    # Trading cycle — every 30 min, Mon-Fri, 9:00 AM–3:30 PM ET
    # CronTrigger fires at :00 and :30 of each hour from 9–15 inclusive.
    scheduler.add_job(
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

    # Reflection — daily at 4:15 PM ET
    scheduler.add_job(
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

    # Market regime classification — daily at 9:25 AM ET
    scheduler.add_job(
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

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))

    try:
        # Keep the event loop alive
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Trader shutdown requested")
    finally:
        scheduler.shutdown(wait=False)
        await dispose_engine()
        logger.info("Trader stopped")


if __name__ == "__main__":
    asyncio.run(main())
