"""Pydantic output models for the trading agent loop."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ObservationOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    current_price: float
    price_change_1h_pct: Optional[float] = None
    price_change_24h_pct: Optional[float] = None
    volume_ratio: Optional[float] = None
    technical_bias: Literal["bullish", "bearish", "neutral"]
    rsi: Optional[float] = None
    atr: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_position: Optional[float] = None
    news_sentiment: Literal["positive", "negative", "neutral"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    risk_level: Literal["low", "medium", "high", "very_high"]
    annualized_volatility: Optional[float] = None
    portfolio_state_json: dict = Field(default_factory=dict)
    similar_memories: list[dict] = Field(default_factory=list)
    market_regime: Literal["trending_bull", "trending_bear", "ranging", "high_volatility"]
    signals_json: dict = Field(default_factory=dict)


class TradeDecisionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    position_size_pct: float = Field(ge=0.0, le=1.0)
    suggested_quantity: Optional[float] = None
    entry_price_type: Literal["market", "limit"] = "market"
    limit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    market_regime: str
    signal_alignment_score: float = Field(ge=0.0, le=1.0)
    memory_context_used: bool = False
    risk_override: bool = False


class TradeExecutionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    order_submitted: bool
    alpaca_order_id: Optional[str] = None
    side: Optional[Literal["buy", "sell"]] = None
    quantity: Optional[float] = None
    order_type: str = "market"
    status: str = "skipped"
    error: Optional[str] = None
    skipped_reason: Optional[str] = None


class ReflectionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime
    position_id: str
    outcome: Literal["profitable", "loss", "breakeven", "inconclusive"]
    pnl_pct: Optional[float] = None
    what_worked: str
    what_failed: str
    signal_accuracy: dict[str, bool] = Field(default_factory=dict)
    prediction_vs_reality: str
    lessons_learned: str
    should_store_memory: bool
    memory_importance_score: float = Field(ge=0.0, le=1.0)
