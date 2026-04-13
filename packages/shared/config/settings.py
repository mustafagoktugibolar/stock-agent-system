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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
