"""Reflection agent — LLM-driven post-trade self-critique.

Receives a position's entry context and current/exit price, then generates a
structured ReflectionOutput with signal accuracy, lessons learned, and a
decision on whether to store the trade as a retrievable memory.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.trading_agent.models.trading_output import ReflectionOutput
from packages.trading_agent.state.trading_state import TradingState

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "reflection_prompt.txt"


def _classify_outcome(pnl_pct: float) -> str:
    if pnl_pct > 2.0:
        return "profitable"
    if pnl_pct < -2.0:
        return "loss"
    if abs(pnl_pct) <= 0.5:
        return "breakeven"
    return "inconclusive"


def reflection_agent(state: TradingState) -> dict[str, Any]:
    """LangGraph node: evaluates a single position and generates a reflection.

    Reads current_position_for_reflection and original_decision_for_reflection
    from state. Returns a ReflectionOutput and updates the state.
    """
    position = state.get("current_position_for_reflection")
    decision = state.get("original_decision_for_reflection")

    if not position:
        return {
            "current_agent": "reflection",
            "errors": ["reflection_agent: no position to reflect on"],
        }

    symbol = position.get("symbol", "UNKNOWN")
    position_id = str(position.get("id", ""))
    entry_price = float(position.get("entry_price", 0.0))
    current_price = float(position.get("current_price_for_reflection", entry_price))
    side = position.get("side", "long")
    quantity = float(position.get("quantity", 0.0))
    status = position.get("status", "open")
    opened_at = position.get("opened_at", "")

    # Compute PnL
    if side == "long":
        pnl_pct = (current_price - entry_price) / entry_price * 100 if entry_price > 0 else 0.0
    else:
        pnl_pct = (entry_price - current_price) / entry_price * 100 if entry_price > 0 else 0.0

    outcome = _classify_outcome(pnl_pct)

    logger.info(
        "[reflection] %s position_id=%s pnl=%.2f%% outcome=%s",
        symbol, position_id, pnl_pct, outcome,
    )

    # Decision context for the prompt
    original_reasoning = (decision or {}).get("reasoning", "No original reasoning available.")
    original_signals = json.dumps((decision or {}).get("signals_json", {}), indent=2)
    market_regime = (decision or {}).get("market_regime", "unknown")

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
        timeout=60,
        max_retries=1,
    )
    # function_calling mode: strict json_schema rejects the free-form
    # signal_accuracy dict[str, bool] field with a 400 error.
    structured_llm = llm.with_structured_output(ReflectionOutput, method="function_calling")

    system_prompt = _PROMPT_PATH.read_text().format(
        symbol=symbol,
        position_id=position_id,
        side=side,
        quantity=quantity,
        entry_price=f"{entry_price:.4f}",
        current_price=f"{current_price:.4f}",
        position_status=status,
        opened_at=opened_at,
        reflected_at=datetime.now(timezone.utc).isoformat(),
        pnl_pct=pnl_pct,
        outcome=outcome,
        original_reasoning=original_reasoning,
        original_signals=original_signals,
        market_regime=market_regime,
    )

    try:
        reflection: ReflectionOutput = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Generate a rigorous reflection for this {symbol} {side} trade. "
                    f"The position {status} with a {pnl_pct:+.2f}% PnL. "
                    f"Follow all reflection instructions precisely."
                )
            ),
        ])
    except Exception as e:
        logger.error("[reflection] Structured output failed for %s: %s", symbol, e)
        return {
            "current_agent": "reflection",
            "errors": [f"reflection_agent failed: {e}"],
        }

    logger.info(
        "[reflection] %s: outcome=%s store_memory=%s importance=%.2f",
        symbol, reflection.outcome, reflection.should_store_memory, reflection.memory_importance_score,
    )
    return {
        "reflection": reflection,
        "current_agent": "reflection",
    }
