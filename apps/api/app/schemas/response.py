from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from packages.agent_core.models.agent_output import (
    FinalRecommendation,
    NewsOutput,
    RiskOutput,
    TechnicalOutput,
)


class AnalysisResponse(BaseModel):
    analysis_id: str
    symbol: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    completed_at: Optional[datetime] = None
    recommendation: Optional[FinalRecommendation] = None
    technical_analysis: Optional[TechnicalOutput] = None
    news_analysis: Optional[NewsOutput] = None
    risk_analysis: Optional[RiskOutput] = None
    errors: list[str] = Field(default_factory=list)
    cached: bool = False


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    symbol: str
    status: Literal["pending", "running", "completed", "failed"]
    progress_pct: int = Field(ge=0, le=100)
