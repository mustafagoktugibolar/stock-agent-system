from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TechnicalSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    indicator: str
    value: float
    signal: Literal["bullish", "bearish", "neutral"]
    description: str


class TechnicalOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    signals: list[TechnicalSignal]
    overall_technical_bias: Literal["bullish", "bearish", "neutral"]
    support_levels: list[float]
    resistance_levels: list[float]
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


class NewsItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    source: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    summary: str


class NewsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    news_items: list[NewsItem]
    overall_sentiment: Literal["positive", "negative", "neutral"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


class RiskMetric(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_name: str
    value: float
    interpretation: str


class RiskOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    metrics: list[RiskMetric]
    risk_level: Literal["low", "medium", "high", "very_high"]
    volatility_percentile: float = Field(ge=0.0, le=100.0)
    max_drawdown: float
    beta: Optional[float] = None
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


# ── Company Profile & Financials ─────────────────────────────────────────────


class CompanyProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    current_price: Optional[float] = None
    currency: str = "USD"
    exchange: Optional[str] = None
    website: Optional[str] = None
    employees: Optional[int] = None


class FinancialLineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    values: dict[str, Optional[float]]


class FinancialStatements(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    balance_sheet: list[FinancialLineItem]
    income_statement: list[FinancialLineItem]
    cash_flow: list[FinancialLineItem]
    periods: list[str]


class FinalRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: float = Field(ge=0.0, le=1.0)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    time_horizon: Literal["short_term", "medium_term", "long_term"]
    reasoning: str
    technical_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    news_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    risk_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    technical_summary: str
    news_summary: str
    risk_summary: str
