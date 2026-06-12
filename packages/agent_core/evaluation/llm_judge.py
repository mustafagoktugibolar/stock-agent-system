"""LLM-as-a-judge node — independent evaluation of the final recommendation.

Runs after the supervisor as the last node in the analysis graph. A separate
LLM call (no tools) reviews the specialist agent outputs against the final
recommendation and scores coherence, evidence grounding, and risk alignment.
This is the LLM-in-the-loop evaluation layer: the supervisor decides, the
judge independently checks whether that decision was justified.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from packages.agent_core.models.agent_output import JudgeVerdict
from packages.agent_core.state.agent_state import AgentState
from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "llm_judge_prompt.txt"


def _format_analysis(obj: Any) -> str:
    if obj is None:
        return "Not available."
    return obj.model_dump_json(indent=2)


def llm_judge_agent(state: AgentState) -> dict[str, Any]:
    """LangGraph node: evaluates the supervisor's FinalRecommendation.

    Does NOT use tools — reads all agent outputs and the final recommendation
    from state and produces a JudgeVerdict via structured output. If the
    supervisor failed (no recommendation), the run is judged a fail without
    spending an LLM call.
    """
    symbol = state["symbol"]
    final = state.get("final_recommendation")

    if final is None:
        logger.warning("[llm_judge] No final recommendation for %s — auto fail", symbol)
        return {
            "judge_verdict": JudgeVerdict(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                verdict="fail",
                overall_score=0.0,
                coherence_score=0.0,
                evidence_score=0.0,
                risk_alignment_score=0.0,
                critique="The supervisor did not produce a final recommendation; there is nothing to evaluate.",
                suggestions=["Inspect state['errors'] for the upstream agent failure."],
            ),
            "current_agent": "llm_judge",
        }

    logger.info("[llm_judge] Evaluating final recommendation for %s", symbol)

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.0,
        timeout=45,
        max_retries=1,
    )
    structured_llm = llm.with_structured_output(JudgeVerdict)

    language = state.get("language", "en")
    lang_instruction = (
        "IMPORTANT: You MUST write `critique` and `suggestions` in Turkish while keeping financial acronyms intact."
        if language == "tr"
        else ""
    )

    system_prompt = _PROMPT_PATH.read_text().format(
        symbol=symbol,
        technical_analysis=_format_analysis(state.get("technical_analysis")),
        news_analysis=_format_analysis(state.get("news_analysis")),
        risk_analysis=_format_analysis(state.get("risk_analysis")),
        company_profile=_format_analysis(state.get("company_profile")),
        final_recommendation=_format_analysis(final),
        language_directive=lang_instruction,
    )

    try:
        verdict: JudgeVerdict = structured_llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=(
                        f"Evaluate the final recommendation for {symbol} against the "
                        f"agent outputs above and return your verdict."
                    )
                ),
            ]
        )
    except Exception as e:
        logger.error("[llm_judge] Structured output extraction failed: %s", e)
        return {
            "current_agent": "llm_judge",
            "errors": [f"llm_judge_agent failed: {e}"],
        }

    logger.info(
        "[llm_judge] Verdict for %s: %s (overall=%.2f, coherence=%.2f, evidence=%.2f, risk=%.2f)",
        symbol,
        verdict.verdict,
        verdict.overall_score,
        verdict.coherence_score,
        verdict.evidence_score,
        verdict.risk_alignment_score,
    )
    return {
        "judge_verdict": verdict,
        "current_agent": "llm_judge",
    }
