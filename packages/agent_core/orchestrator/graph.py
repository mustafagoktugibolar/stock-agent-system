"""LangGraph StateGraph for multi-agent stock analysis."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from packages.agent_core.agents.fundamentals_agent import fundamentals_agent
from packages.agent_core.agents.news_agent import news_agent
from packages.agent_core.agents.risk_agent import risk_agent
from packages.agent_core.agents.supervisor_agent import supervisor_agent
from packages.agent_core.agents.technical_agent import technical_agent
from packages.agent_core.state.agent_state import AgentState

# ── Graph definition ──────────────────────────────────────────────────────────

def create_analysis_graph():
    """Build and compile the stock analysis StateGraph.

    Flow:
        START → technical/news/risk/fundamentals (parallel) → supervisor → END

    Each node is a plain function (AgentState) -> dict that returns a partial
    state update.  Errors in any node are collected in state["errors"].
    """
    builder = StateGraph(AgentState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    builder.add_node("technical_agent", technical_agent)
    builder.add_node("news_agent", news_agent)
    builder.add_node("risk_agent", risk_agent)
    builder.add_node("fundamentals_agent", fundamentals_agent)
    builder.add_node("supervisor_agent", supervisor_agent)

    # ── Edges (parallel) ────────────────────────────────────────────────────
    # Run all four specialist agents in parallel from START,
    # then converge to supervisor_agent which aggregates results.
    builder.add_edge(START, "technical_agent")
    builder.add_edge(START, "news_agent")
    builder.add_edge(START, "risk_agent")
    builder.add_edge(START, "fundamentals_agent")

    # Wait until all four branches finish before synthesizing.
    builder.add_edge(
        ["technical_agent", "news_agent", "risk_agent", "fundamentals_agent"],
        "supervisor_agent",
    )

    builder.add_edge("supervisor_agent", END)

    return builder.compile()


@lru_cache(maxsize=1)
def get_analysis_graph():
    """Return the compiled analysis graph, building it once on first call."""
    return create_analysis_graph()

