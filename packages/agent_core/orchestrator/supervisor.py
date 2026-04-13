"""Routing logic for the LangGraph analysis graph."""

from langgraph.constants import END

from packages.agent_core.state.agent_state import AgentState

_MAX_ERRORS = 3


def route_after_technical(state: AgentState) -> str:
    """After technical analysis, proceed to news or abort on too many errors."""
    if len(state.get("errors", [])) >= _MAX_ERRORS:
        return END
    return "news_agent"


def route_after_news(state: AgentState) -> str:
    """After news analysis, proceed to risk or abort on too many errors."""
    if len(state.get("errors", [])) >= _MAX_ERRORS:
        return END
    return "risk_agent"


def route_after_risk(state: AgentState) -> str:
    """After risk analysis, always proceed to supervisor (partial results are fine)."""
    return "supervisor_agent"
