"""Async SQLAlchemy engine, session factory, and table lifecycle helpers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.shared.config.settings import get_settings
from packages.shared.db.base import Base
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        # SQLAlchemy async requires +asyncpg driver
        url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(
            url,
            echo=settings.app_env == "development",
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def create_tables() -> None:
    """Create all ORM-mapped tables if they don't already exist.

    Called once during FastAPI startup via the lifespan context manager.
    """
    # Side-effect import ensures ORM metadata is populated before create_all
    import packages.shared.db.models.analysis  # noqa: F401
    import packages.shared.db.models.backtest   # noqa: F401

    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")


async def dispose_engine() -> None:
    """Release all database connections. Called on FastAPI shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a transactional AsyncSession."""
    async with get_session_factory()() as session:
        yield session
