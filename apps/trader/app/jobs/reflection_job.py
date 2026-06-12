"""Daily reflection job — runs at 4:15 PM ET after market close.

Queries positions that have passed the reflection window and invokes the
reflection graph to generate structured self-critiques and store memories.
"""

from packages.shared.logging.logger import get_logger
from packages.trading_agent.orchestrator.reflection_graph import get_reflection_graph
from packages.shared.config.settings import get_settings

logger = get_logger(__name__)


async def run_reflection() -> None:
    """Invoke the reflection graph for all positions due for analysis."""
    settings = get_settings()
    graph = get_reflection_graph()

    logger.info(
        "Reflection job starting (window=%dh)",
        settings.reflection_window_hours,
    )

    initial_state = {
        "session_id": "",
        "symbol": "",
        "watchlist": settings.trading_watchlist,
        "messages": [],
        "observation": None,
        "portfolio_state": None,
        "retrieved_memories": [],
        "memory_context_text": None,
        "trade_decision": None,
        "execution_result": None,
        "positions_to_reflect": [],
        "current_position_for_reflection": None,
        "original_decision_for_reflection": None,
        "reflection": None,
        "current_agent": "start",
        "errors": [],
        "market_regime": None,
        "trading_enabled": settings.trading_enabled,
        "circuit_breaker_active": False,
    }

    try:
        # Each reflected position costs ~4 graph supersteps; the default
        # recursion limit (25) would abort after ~6 of the up-to-20 positions
        # the fetch query can return.
        await graph.ainvoke(initial_state, config={"recursion_limit": 150})
        logger.info("Reflection job completed")
    except Exception as e:
        logger.error("Reflection job failed: %s", e)
