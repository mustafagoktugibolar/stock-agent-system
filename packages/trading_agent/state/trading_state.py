"""TradingState — the shared state contract for both trading graphs."""

from typing import Annotated, Optional, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from packages.trading_agent.models.trading_output import (
    ObservationOutput,
    ReflectionOutput,
    TradeDecisionOutput,
    TradeExecutionOutput,
)


def _append_errors(left: list[str], right: list[str]) -> list[str]:
    return left + right


class TradingState(TypedDict):
    # ── Session context ───────────────────────────────────────────────────────
    session_id: str
    symbol: str
    watchlist: list[str]

    # ── Message history (append-only, same pattern as AgentState) ────────────
    messages: Annotated[Sequence[AnyMessage], add_messages]

    # ── Observation layer ─────────────────────────────────────────────────────
    observation: Optional[ObservationOutput]
    portfolio_state: Optional[dict]

    # ── A2A: Analysis agent context (fetched from analysis API cache) ─────────
    analysis_context: Optional[dict]

    # ── Memory layer ──────────────────────────────────────────────────────────
    retrieved_memories: list[dict]
    memory_context_text: Optional[str]

    # ── Decision layer ────────────────────────────────────────────────────────
    trade_decision: Optional[TradeDecisionOutput]

    # ── Execution layer ───────────────────────────────────────────────────────
    execution_result: Optional[TradeExecutionOutput]

    # ── Reflection layer ──────────────────────────────────────────────────────
    positions_to_reflect: list[dict]
    current_position_for_reflection: Optional[dict]
    original_decision_for_reflection: Optional[dict]
    reflection: Optional[ReflectionOutput]

    # ── Control ───────────────────────────────────────────────────────────────
    current_agent: str
    errors: Annotated[list[str], _append_errors]
    market_regime: Optional[str]
    trading_enabled: bool
    circuit_breaker_active: bool
