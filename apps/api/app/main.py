"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from packages.shared.config.settings import get_settings  # noqa: E402
from packages.shared.logging.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

# Module-level Redis client — initialized in lifespan
redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    settings = get_settings()

    redis_client = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Redis connected: %s", settings.redis_url)

    from packages.shared.db.session import create_tables, dispose_engine  # noqa: PLC0415
    await create_tables()

    yield

    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection closed")
    await dispose_engine()


app = FastAPI(
    title="Stock Agent API",
    description="Multi-agent AI system for real-time stock analysis and investment recommendations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from apps.api.app.api.routes import router  # noqa: E402

app.include_router(router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Simple health check — verifies Redis connectivity."""
    try:
        assert redis_client is not None
        await redis_client.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {e}"

    return {"status": "ok", "redis": redis_status}
