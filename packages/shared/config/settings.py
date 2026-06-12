from functools import lru_cache
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Alpaca Markets
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_url: str = "https://data.alpaca.markets"

    # PostgreSQL
    database_url: str = "postgresql://postgres:postgres@localhost:5432/stockagent"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "stock-agent"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    analysis_cache_ttl: int = 300
    analysis_api_url: str = "http://localhost:8000"

    # Trading Agent — master kill switch (default OFF for safety)
    trading_enabled: bool = False
    trading_watchlist: list[str] = ["AAPL", "MSFT", "NVDA", "SPY"]
    max_open_positions: int = 5
    max_position_size_usd: float = 1000.0
    max_daily_drawdown_pct: float = 3.0
    reflection_window_hours: int = 24
    trading_cycle_interval_minutes: int = 30
    min_decision_confidence: float = 0.60
    trading_strategy_version: str = "v1"
    max_hold_days: int = 5

    # Virtual portfolio (used in dry-run / simulated mode)
    virtual_starting_capital: float = 100_000.0

    # Memory / pgvector
    memory_similarity_threshold: float = 0.75
    memory_retrieval_limit: int = 5
    embedding_model: str = "text-embedding-3-small"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
