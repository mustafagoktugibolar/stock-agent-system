"""Backtest orchestration — runs the engine in a worker thread, tracks via Redis.

The engine is synchronous (sync LLM calls), so it runs in the default executor.
Progress and results are written to Redis with a sync client (safe inside the
executor thread) under backtest:{id} with a 24h TTL, and the frontend polls
GET /api/v1/trader/backtest/{id}.
"""

import asyncio
import json
import uuid
from datetime import date, datetime, timezone

import redis as sync_redis

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.trading_agent.backtest.engine import run_backtest

logger = get_logger(__name__)

_KEY_PREFIX = "backtest:"
_TTL_SECONDS = 86_400


def _redis_key(backtest_id: str) -> str:
    return f"{_KEY_PREFIX}{backtest_id}"


def _run_in_thread(
    backtest_id: str,
    symbols: list[str],
    start_date: date,
    end_date: date,
    initial_capital: float,
    min_confidence: float,
) -> None:
    settings = get_settings()
    r = sync_redis.Redis.from_url(settings.redis_url, decode_responses=True)
    key = _redis_key(backtest_id)

    def _write(payload: dict) -> None:
        r.setex(key, _TTL_SECONDS, json.dumps(payload))

    def _progress(progress: dict) -> None:
        _write({
            "backtest_id": backtest_id,
            "status": "running",
            "progress": progress,
            "started_at": started_at,
        })

    started_at = datetime.now(timezone.utc).isoformat()
    try:
        result = run_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            min_confidence=min_confidence,
            progress_cb=_progress,
        )
        _write({
            "backtest_id": backtest_id,
            "status": "completed",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
        })
        logger.info(
            "Backtest %s completed: %s → %.2f%% return, %d trades",
            backtest_id, symbols, result["total_return_pct"], result["total_trades"],
        )
    except Exception as e:
        logger.error("Backtest %s failed: %s", backtest_id, e)
        _write({
            "backtest_id": backtest_id,
            "status": "failed",
            "started_at": started_at,
            "error": str(e),
        })
    finally:
        r.close()


class BacktestService:
    async def start(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
        initial_capital: float,
        min_confidence: float,
    ) -> dict:
        backtest_id = str(uuid.uuid4())

        settings = get_settings()
        r = sync_redis.Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            r.setex(
                _redis_key(backtest_id),
                _TTL_SECONDS,
                json.dumps({"backtest_id": backtest_id, "status": "starting"}),
            )
        finally:
            r.close()

        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            None,
            _run_in_thread,
            backtest_id, symbols, start_date, end_date, initial_capital, min_confidence,
        )
        return {"backtest_id": backtest_id, "status": "starting"}

    async def get(self, backtest_id: str) -> dict | None:
        settings = get_settings()
        r = sync_redis.Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            raw = r.get(_redis_key(backtest_id))
        finally:
            r.close()
        return json.loads(raw) if raw else None


_instance: BacktestService | None = None


def get_backtest_service() -> BacktestService:
    global _instance
    if _instance is None:
        _instance = BacktestService()
    return _instance
