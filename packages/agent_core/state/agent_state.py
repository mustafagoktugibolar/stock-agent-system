from typing import Annotated, Optional, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from packages.agent_core.models.agent_output import (
    CompanyProfile,
    FinalRecommendation,
    FinancialStatements,
    NewsOutput,
    RiskOutput,
    TechnicalOutput,
)


def _append_errors(left: list[str], right: list[str]) -> list[str]:
    return left + right


class AgentState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────────────
    symbol: str
    timeframe: str          # "1d", "1h", "5m"
    language: str           # "en" or "tr"
    analysis_id: str        # UUID for tracking / caching

    # ── Message history (append-only via add_messages reducer) ───────────────
    messages: Annotated[Sequence[AnyMessage], add_messages]

    # ── Agent outputs (last-write-wins; overwritten by each agent node) ───────
    technical_analysis: Optional[TechnicalOutput]
    news_analysis: Optional[NewsOutput]
    risk_analysis: Optional[RiskOutput]
    company_profile: Optional[CompanyProfile]
    financial_statements: Optional[FinancialStatements]
    final_recommendation: Optional[FinalRecommendation]

    # ── Control ───────────────────────────────────────────────────────────────
    current_agent: str
    errors: Annotated[list[str], _append_errors]

