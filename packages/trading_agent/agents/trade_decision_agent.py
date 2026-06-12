"""Trade decision agent — LLM-driven BUY/SELL/HOLD reasoning.

Mirrors supervisor_agent.py: single structured-output LLM call, no tool loop.
Reads all context from TradingState and produces TradeDecisionOutput.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.trading_agent.models.trading_output import TradeDecisionOutput
from packages.trading_agent.state.trading_state import TradingState

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "trade_decision_prompt.txt"


def _format_analysis_context(ctx: dict | None) -> str:
    """Format the A2A analysis agent context into a readable summary."""
    if not ctx:
        return "No analysis agent context available (cache miss or API unreachable)."

    rec = ctx.get("recommendation") or {}
    tech = ctx.get("technical_analysis") or {}
    news = ctx.get("news_analysis") or {}
    risk = ctx.get("risk_analysis") or {}
    profile = ctx.get("company_profile") or {}

    lines: list[str] = []

    # Supervisor recommendation
    action = rec.get("recommendation", "N/A")
    confidence = rec.get("confidence")
    conf_str = f"{confidence * 100:.0f}%" if confidence is not None else "N/A"
    target = rec.get("target_price")
    stop = rec.get("stop_loss")
    horizon = rec.get("time_horizon", "N/A")
    lines.append(f"Supervisor Recommendation: {action} (confidence {conf_str}, horizon {horizon})")
    if target:
        lines.append(f"  Target Price: ${target:.2f}")
    if stop:
        lines.append(f"  Stop Loss: ${stop:.2f}")
    if rec.get("reasoning"):
        lines.append(f"  Reasoning: {rec['reasoning'][:400]}")

    # Technical summary
    if tech.get("overall_technical_bias"):
        lines.append(f"\nTechnical Agent Bias: {tech['overall_technical_bias']} (confidence {tech.get('confidence', 0) * 100:.0f}%)")
    if tech.get("summary"):
        lines.append(f"  Summary: {tech['summary'][:300]}")
    signals = tech.get("signals") or []
    if signals:
        sig_lines = [f"    {s['indicator']}: {s['signal'].upper()} ({s['description'][:60]})" for s in signals[:5]]
        lines.append("  Key Signals:\n" + "\n".join(sig_lines))

    # News summary
    if news.get("overall_sentiment"):
        lines.append(f"\nNews Agent Sentiment: {news['overall_sentiment']} (score {news.get('sentiment_score', 0):+.2f})")
    if news.get("summary"):
        lines.append(f"  Summary: {news['summary'][:300]}")

    # Risk summary
    if risk.get("risk_level"):
        lines.append(f"\nRisk Agent Assessment: {risk['risk_level'].upper()} risk")
    if risk.get("summary"):
        lines.append(f"  Summary: {risk['summary'][:300]}")

    # Company info
    if profile.get("name"):
        sector = profile.get("sector", "N/A")
        mktcap = profile.get("market_cap")
        mktcap_str = f"${mktcap / 1e9:.1f}B" if mktcap else "N/A"
        lines.append(f"\nCompany: {profile['name']} | Sector: {sector} | Market Cap: {mktcap_str}")

    return "\n".join(lines)


def _format_memories(memories: list[dict]) -> str:
    if not memories:
        return "No similar past situations found in memory."
    lines = []
    for i, m in enumerate(memories, 1):
        sim = m.get("similarity", 0.0)
        outcome = m.get("outcome_label", "unknown")
        pnl = m.get("pnl_pct")
        pnl_str = f"{pnl:+.2f}%" if pnl is not None else "N/A"
        regime = m.get("market_regime", "unknown")
        lessons = m.get("lessons_text", "")
        situation = m.get("situation_text", "")
        lines.append(
            f"Memory {i} (similarity={sim:.2f}, outcome={outcome}, PnL={pnl_str}, regime={regime}):\n"
            f"  Situation: {situation[:200]}\n"
            f"  Lessons: {lessons[:300]}"
        )
    return "\n\n".join(lines)


def _signal_inventory(observation: Any, has_open_position: bool) -> str:
    """Deterministically classify signals so the LLM doesn't have to count.

    The LLM repeatedly miscounted its own signal inventory and defaulted to
    HOLD; the counting rule is mechanical, so it is computed in code and the
    LLM keeps only the veto/judgment role.
    """
    bullish: list[str] = []
    bearish: list[str] = []
    neutral: list[str] = []

    regime = observation.market_regime
    if regime == "trending_bull":
        bullish.append(f"market_regime={regime}")
    elif regime == "trending_bear":
        bearish.append(f"market_regime={regime}")
    else:
        neutral.append(f"market_regime={regime}")

    if observation.rsi is not None:
        if observation.rsi < 40:
            bullish.append(f"rsi={observation.rsi:.1f} (oversold)")
        elif observation.rsi > 70:
            bearish.append(f"rsi={observation.rsi:.1f} (overbought)")
        else:
            neutral.append(f"rsi={observation.rsi:.1f}")

    if observation.macd_histogram is not None:
        if observation.macd_histogram > 0:
            bullish.append(f"macd_histogram={observation.macd_histogram:+.4f}")
        else:
            bearish.append(f"macd_histogram={observation.macd_histogram:+.4f}")

    if observation.bb_position is not None:
        if observation.bb_position < 0.30:
            bullish.append(f"bb_position={observation.bb_position:.2f} (near lower band)")
        elif observation.bb_position > 0.85:
            bearish.append(f"bb_position={observation.bb_position:.2f} (near upper band)")
        else:
            neutral.append(f"bb_position={observation.bb_position:.2f}")

    if observation.price_change_24h_pct is not None:
        if observation.price_change_24h_pct > 1.5:
            bullish.append(f"price_change_24h={observation.price_change_24h_pct:+.2f}%")
        elif observation.price_change_24h_pct < -1.5:
            bearish.append(f"price_change_24h={observation.price_change_24h_pct:+.2f}%")
        else:
            neutral.append(f"price_change_24h={observation.price_change_24h_pct:+.2f}%")

    if observation.sentiment_score > 0.15:
        bullish.append(f"sentiment={observation.sentiment_score:+.2f}")
    elif observation.sentiment_score < -0.15:
        bearish.append(f"sentiment={observation.sentiment_score:+.2f}")
    else:
        neutral.append(f"sentiment={observation.sentiment_score:+.2f}")

    if len(bullish) > len(bearish) and len(bullish) >= 2:
        verdict = (
            f"RULE VERDICT: BUY conditions are met (bullish {len(bullish)} > bearish {len(bearish)}, "
            f"at least 2 bullish). The rule-consistent action is BUY at confidence 0.60-0.75. "
            f"Deviate to HOLD only if you identify a specific disqualifying risk, and name it explicitly."
        )
    elif len(bearish) > len(bullish) and has_open_position:
        verdict = (
            f"RULE VERDICT: bearish signals outnumber bullish ({len(bearish)} > {len(bullish)}) and a "
            f"position is open in this symbol. The rule-consistent action is SELL to exit."
        )
    else:
        verdict = (
            f"RULE VERDICT: no qualifying majority (bullish {len(bullish)}, bearish {len(bearish)}). "
            f"The rule-consistent action is HOLD."
        )

    return (
        f"BULLISH ({len(bullish)}): {', '.join(bullish) or 'none'}\n"
        f"BEARISH ({len(bearish)}): {', '.join(bearish) or 'none'}\n"
        f"NEUTRAL ({len(neutral)}): {', '.join(neutral) or 'none'}\n"
        f"{verdict}"
    )


def trade_decision_agent(state: TradingState) -> dict[str, Any]:
    """LangGraph node: LLM decides BUY/SELL/HOLD with full reasoning chain.

    No tools — reads observation and memories from state, calls structured
    output LLM once, returns TradeDecisionOutput.
    """
    symbol = state["symbol"]
    observation = state.get("observation")
    portfolio = state.get("portfolio_state") or {}
    memories = state.get("retrieved_memories") or []
    analysis_context = state.get("analysis_context")

    logger.info(
        "[trade_decision] Deciding for %s (memories=%d, a2a_context=%s)",
        symbol, len(memories), "yes" if analysis_context else "no",
    )

    if observation is None:
        return {
            "current_agent": "trade_decision",
            "errors": [f"trade_decision_agent: no observation for {symbol}"],
        }

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        timeout=60,
        max_retries=1,
    )
    structured_llm = llm.with_structured_output(TradeDecisionOutput)

    memory_context = _format_memories(memories)
    analysis_agent_context = _format_analysis_context(analysis_context)
    has_open_position = symbol in (portfolio.get("open_position_symbols") or [])
    signal_inventory = _signal_inventory(observation, has_open_position)

    system_prompt = _PROMPT_PATH.read_text().format(
        symbol=symbol,
        signal_inventory=signal_inventory,
        current_price=f"{observation.current_price:.4f}",
        market_regime=observation.market_regime,
        timestamp=observation.timestamp.isoformat(),
        rsi=f"{observation.rsi:.2f}" if observation.rsi is not None else "N/A",
        macd_histogram=f"{observation.macd_histogram:.4f}" if observation.macd_histogram is not None else "N/A",
        atr=f"{observation.atr:.4f}" if observation.atr is not None else "N/A",
        bb_position=f"{observation.bb_position:.3f}" if observation.bb_position is not None else "N/A",
        technical_bias=observation.technical_bias,
        price_change_24h_pct=f"{observation.price_change_24h_pct:.2f}" if observation.price_change_24h_pct is not None else "N/A",
        price_change_1h_pct=f"{observation.price_change_1h_pct:.2f}" if observation.price_change_1h_pct is not None else "N/A",
        volume_ratio=f"{observation.volume_ratio:.2f}" if observation.volume_ratio is not None else "N/A",
        news_sentiment=observation.news_sentiment,
        sentiment_score=f"{observation.sentiment_score:.3f}",
        risk_level=observation.risk_level,
        annualized_volatility=f"{observation.annualized_volatility:.1f}" if observation.annualized_volatility is not None else "N/A",
        current_equity=f"{portfolio.get('current_equity', 0.0):.2f}",
        available_cash=f"{portfolio.get('cash', 0.0):.2f}",
        open_position_count=portfolio.get("total_open_positions", 0),
        open_position_symbols=", ".join(portfolio.get("open_position_symbols", [])) or "none",
        circuit_breaker_active=portfolio.get("circuit_breaker_active", False),
        daily_pnl_pct=f"{portfolio.get('daily_pnl_pct', 0.0):.2f}",
        memory_context=memory_context,
        analysis_agent_context=analysis_agent_context,
    )

    try:
        decision: TradeDecisionOutput = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Based on the market observation and memory context above, "
                    f"produce a trading decision for {symbol}. "
                    f"Follow all decision instructions precisely."
                )
            ),
        ])
    except Exception as e:
        logger.error("[trade_decision] Structured output failed for %s: %s", symbol, e)
        return {
            "current_agent": "trade_decision",
            "errors": [f"trade_decision_agent failed: {e}"],
        }

    logger.info(
        "[trade_decision] %s: action=%s confidence=%.2f alignment=%.2f",
        symbol, decision.action, decision.confidence, decision.signal_alignment_score,
    )
    return {
        "trade_decision": decision,
        "current_agent": "trade_decision",
        "memory_context_text": memory_context,
    }
