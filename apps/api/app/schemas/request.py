from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=24,
        description="Stock ticker symbol, including exchange suffix when needed",
    )
    timeframe: Literal["1d", "1h", "5m"] = Field(default="1d", description="Bar interval")
    language: Literal["en", "tr"] = Field(default="en", description="Response language")
    force_refresh: bool = Field(
        default=False, description="Bypass cache and run a fresh analysis"
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.upper().strip()
