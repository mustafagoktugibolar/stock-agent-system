"""Supervisor agent node — synthesizes all analyses into a final recommendation."""

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from packages.agent_core.models.agent_output import FinalRecommendation
from packages.agent_core.state.agent_state import AgentState
from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "supervisor_prompt.txt"


def _format_analysis(obj: Any) -> str:
    """Serialize an agent output model to a readable string for the LLM prompt."""
    if obj is None:
        return "Not available."
    return obj.model_dump_json(indent=2)


def supervisor_agent(state: AgentState) -> dict[str, Any]:
    """LangGraph node: synthesizes technical, news, and risk analyses.

    Does NOT use tools — reads the three completed analyses directly from
    state and produces a single FinalRecommendation via structured output.
    """
    symbol = state["symbol"]
    logger.info("[supervisor_agent] Synthesizing analyses for %s", symbol)

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        timeout=45,
        max_retries=1,
    )
    structured_llm = llm.with_structured_output(FinalRecommendation)

    technical_str = _format_analysis(state.get("technical_analysis"))
    news_str = _format_analysis(state.get("news_analysis"))
    risk_str = _format_analysis(state.get("risk_analysis"))

    system_prompt = _PROMPT_PATH.read_text().format(
        symbol=symbol,
        technical_analysis=technical_str,
        news_analysis=news_str,
        risk_analysis=risk_str,
    )

    try:
        final: FinalRecommendation = structured_llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=(
                        f"Based on the three analyses above, produce the final investment "
                        f"recommendation for {symbol}."
                    )
                ),
            ]
        )
    except Exception as e:
        logger.error("[supervisor_agent] Structured output extraction failed: %s", e)
        return {
            "current_agent": "supervisor",
            "errors": [f"supervisor_agent failed: {e}"],
        }

    logger.info(
        "[supervisor_agent] Final recommendation for %s: %s (confidence=%.2f)",
        symbol,
        final.recommendation,
        final.confidence,
    )
    return {
        "final_recommendation": final,
        "current_agent": "supervisor",
    }
