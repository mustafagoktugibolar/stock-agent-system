"""LangGraph StateGraph for multi-agent stock analysis."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from packages.analysis_agent.agents.fundamentals_agent import fundamentals_agent
from packages.analysis_agent.agents.news_agent import news_agent
from packages.analysis_agent.agents.risk_agent import risk_agent
from packages.analysis_agent.agents.supervisor_agent import supervisor_agent
from packages.analysis_agent.agents.technical_agent import technical_agent
from packages.analysis_agent.evaluation.llm_judge import llm_judge_agent
from packages.analysis_agent.state.agent_state import AgentState

# ── Graph definition ──────────────────────────────────────────────────────────

def create_analysis_graph():
    """Build and compile the stock analysis StateGraph.

    Flow:
        START → technical/news/risk/fundamentals (parallel) → supervisor → llm_judge → END

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
    builder.add_node("llm_judge", llm_judge_agent)

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

    # LLM-in-the-loop evaluation: an independent judge reviews the
    # supervisor's recommendation before the run completes.
    builder.add_edge("supervisor_agent", "llm_judge")
    builder.add_edge("llm_judge", END)

    return builder.compile()


@lru_cache(maxsize=1)
def get_analysis_graph():
    """Return the compiled analysis graph, building it once on first call."""
    return create_analysis_graph()

