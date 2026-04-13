"""FastAPI route definitions for the stock analysis API."""

import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect

from apps.api.app.schemas.request import AnalysisRequest
from apps.api.app.schemas.response import AnalysisResponse, AnalysisStatusResponse
from apps.api.app.services.analysis_service import AnalysisService
from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_redis() -> aioredis.Redis:
    from apps.api.app.main import redis_client  # noqa: PLC0415
    return redis_client


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/analyze/sync",
    response_model=AnalysisResponse,
    summary="Run analysis and wait for result (≈30-60s)",
)
async def analyze_sync(
    request: AnalysisRequest,
    redis: aioredis.Redis = Depends(get_redis),
) -> AnalysisResponse:
    """Trigger analysis and block until it completes.

    Suitable for development and simple frontend polling.
    Results are cached in Redis for `ANALYSIS_CACHE_TTL` seconds.
    """
    service = AnalysisService(redis)
    return await service.run_analysis(
        symbol=request.symbol,
        timeframe=request.timeframe,
        force_refresh=request.force_refresh,
    )


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=202,
    summary="Trigger async analysis (returns immediately)",
)
async def analyze_async(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    redis: aioredis.Redis = Depends(get_redis),
) -> AnalysisResponse:
    """Trigger analysis in the background and return a pending response immediately.

    Poll `GET /api/v1/analysis/{symbol}` to retrieve the result once it's ready.
    """
    analysis_id = str(uuid.uuid4())
    service = AnalysisService(redis)
    background_tasks.add_task(
        service.run_analysis,
        request.symbol,
        request.timeframe,
        request.force_refresh,
    )
    return AnalysisResponse(
        analysis_id=analysis_id,
        symbol=request.symbol,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )


@router.get(
    "/analysis/{symbol}",
    response_model=AnalysisResponse,
    summary="Retrieve cached analysis for a symbol",
)
async def get_cached_analysis(
    symbol: str,
    timeframe: str = "1d",
    redis: aioredis.Redis = Depends(get_redis),
) -> AnalysisResponse:
    """Return the most recent cached analysis for the given symbol."""
    symbol = symbol.upper().strip()
    cache_key = f"analysis:{symbol}:{timeframe}"
    try:
        raw = await redis.get(cache_key)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cache unavailable: {e}") from e

    if not raw:
        raise HTTPException(
            status_code=404,
            detail=f"No cached analysis found for {symbol}. Run /analyze/sync first.",
        )
    response = AnalysisResponse.model_validate_json(raw)
    return response.model_copy(update={"cached": True})


@router.delete(
    "/analysis/{symbol}",
    status_code=204,
    summary="Invalidate cached analysis for a symbol",
)
async def invalidate_cache(
    symbol: str,
    timeframe: str = "1d",
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """Delete cached analysis from Redis, forcing a fresh run on the next request."""
    symbol = symbol.upper().strip()
    await redis.delete(f"analysis:{symbol}:{timeframe}")


@router.websocket("/ws/analysis/{symbol}")
async def analysis_websocket(websocket: WebSocket, symbol: str) -> None:
    """WebSocket endpoint for real-time analysis progress updates.

    Subscribe to `analysis_progress:<SYMBOL>` Redis channel.
    The analysis service publishes JSON progress events while running.
    """
    symbol = symbol.upper().strip()
    await websocket.accept()
    settings = get_settings()
    redis_sub = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis_sub.pubsub()
    await pubsub.subscribe(f"analysis_progress:{symbol}")
    logger.info("WebSocket client connected for %s", symbol)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for %s", symbol)
    finally:
        await pubsub.unsubscribe(f"analysis_progress:{symbol}")
        await redis_sub.aclose()
