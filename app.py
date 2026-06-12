"""Gradio web interface for the multi-agent stock analysis system.

Hugging Face Spaces entry point (SEN4018 deployment requirement). Wraps the
LangGraph analysis pipeline directly — no FastAPI, Redis, or PostgreSQL
needed. Requires only OPENAI_API_KEY (set as a Space secret); market data
comes from yfinance when Alpaca keys are absent.

Run locally from the repo root:
    OPENAI_API_KEY=sk-... python app.py
"""

import os
from typing import Any, Optional

import gradio as gr

from packages.agent_core.orchestrator.graph import get_analysis_graph
from packages.agent_core.state.agent_state import AgentState

_REC_COLORS = {"BUY": "#16a34a", "HOLD": "#ca8a04", "SELL": "#dc2626"}
_VERDICT_COLORS = {"pass": "#16a34a", "fail": "#dc2626"}


def _confidence_bar(value: float) -> str:
    pct = round(value * 100)
    return f"`{'█' * (pct // 10)}{'░' * (10 - pct // 10)}` **{pct}%**"


def _recommendation_md(rec: Optional[Any]) -> str:
    if rec is None:
        return "### ⚠️ No recommendation produced\nCheck the Errors tab."
    color = _REC_COLORS.get(rec.recommendation, "#6b7280")
    lines = [
        f"## <span style='color:{color}'>{rec.recommendation}</span> — {rec.symbol}",
        f"**Confidence:** {_confidence_bar(rec.confidence)}",
        f"**Time horizon:** {rec.time_horizon.replace('_', ' ')}",
    ]
    if rec.target_price:
        lines.append(f"**Target price:** ${rec.target_price:,.2f}")
    if rec.stop_loss:
        lines.append(f"**Stop loss:** ${rec.stop_loss:,.2f}")
    lines += ["", "### Reasoning", rec.reasoning]
    return "\n\n".join(lines)


def _judge_md(verdict: Optional[Any]) -> str:
    if verdict is None:
        return "### ⚠️ Judge did not run"
    color = _VERDICT_COLORS.get(verdict.verdict, "#6b7280")
    lines = [
        f"## Judge verdict: <span style='color:{color}'>{verdict.verdict.upper()}</span>",
        f"**Overall score:** {_confidence_bar(verdict.overall_score)}",
        "",
        f"| Dimension | Score |",
        f"|---|---|",
        f"| Coherence | {verdict.coherence_score:.2f} |",
        f"| Evidence grounding | {verdict.evidence_score:.2f} |",
        f"| Risk alignment | {verdict.risk_alignment_score:.2f} |",
        "",
        "### Critique",
        verdict.critique,
    ]
    if verdict.suggestions:
        lines += ["", "### Suggestions"] + [f"- {s}" for s in verdict.suggestions]
    return "\n".join(lines)


def _technical_md(t: Optional[Any]) -> str:
    if t is None:
        return "_Not available._"
    rows = "\n".join(
        f"| {s.indicator} | {s.value:.2f} | {s.signal} | {s.description} |"
        for s in t.signals
    )
    return (
        f"**Bias:** {t.overall_technical_bias} — **Confidence:** {t.confidence:.2f}\n\n"
        f"| Indicator | Value | Signal | Description |\n|---|---|---|---|\n{rows}\n\n"
        f"**Support:** {', '.join(f'${x:,.2f}' for x in t.support_levels) or '—'}  \n"
        f"**Resistance:** {', '.join(f'${x:,.2f}' for x in t.resistance_levels) or '—'}\n\n"
        f"{t.summary}"
    )


def _news_md(n: Optional[Any]) -> str:
    if n is None:
        return "_Not available._"
    items = "\n".join(
        f"- **[{a.sentiment_score:+.2f}]** {a.title} _({a.source})_"
        for a in n.news_items
    )
    return (
        f"**Sentiment:** {n.overall_sentiment} ({n.sentiment_score:+.2f}) — "
        f"**Confidence:** {n.confidence:.2f}\n\n{items}\n\n{n.summary}"
    )


def _risk_md(r: Optional[Any]) -> str:
    if r is None:
        return "_Not available._"
    rows = "\n".join(
        f"| {m.metric_name} | {m.value:.3f} | {m.interpretation} |" for m in r.metrics
    )
    return (
        f"**Risk level:** {r.risk_level} — **Confidence:** {r.confidence:.2f}\n\n"
        f"| Metric | Value | Interpretation |\n|---|---|---|\n{rows}\n\n{r.summary}"
    )


def _profile_md(p: Optional[Any]) -> str:
    if p is None:
        return "_Not available._"
    facts = {
        "Sector": p.sector,
        "Industry": p.industry,
        "Market cap": f"${p.market_cap:,.0f}" if p.market_cap else None,
        "P/E": p.pe_ratio,
        "Forward P/E": p.forward_pe,
        "52w high": f"${p.fifty_two_week_high:,.2f}" if p.fifty_two_week_high else None,
        "52w low": f"${p.fifty_two_week_low:,.2f}" if p.fifty_two_week_low else None,
        "Current price": f"${p.current_price:,.2f}" if p.current_price else None,
    }
    rows = "\n".join(f"| {k} | {v} |" for k, v in facts.items() if v is not None)
    return f"### {p.name}\n\n| | |\n|---|---|\n{rows}\n\n{p.description or ''}"


def run_analysis(symbol: str, language: str):
    symbol = (symbol or "").upper().strip()
    if not symbol:
        raise gr.Error("Please enter a stock symbol, e.g. AAPL.")
    if not os.environ.get("OPENAI_API_KEY"):
        raise gr.Error("OPENAI_API_KEY is not configured for this Space.")

    initial_state: AgentState = {
        "symbol": symbol,
        "timeframe": "1d",
        "language": "tr" if language == "Türkçe" else "en",
        "analysis_id": "gradio",
        "messages": [],
        "technical_analysis": None,
        "news_analysis": None,
        "risk_analysis": None,
        "company_profile": None,
        "financial_statements": None,
        "final_recommendation": None,
        "judge_verdict": None,
        "current_agent": "start",
        "errors": [],
    }

    state = get_analysis_graph().invoke(initial_state)

    errors = state.get("errors") or []
    errors_md = "\n".join(f"- {e}" for e in errors) if errors else "_No errors._"

    return (
        _recommendation_md(state.get("final_recommendation")),
        _judge_md(state.get("judge_verdict")),
        _technical_md(state.get("technical_analysis")),
        _news_md(state.get("news_analysis")),
        _risk_md(state.get("risk_analysis")),
        _profile_md(state.get("company_profile")),
        errors_md,
    )


with gr.Blocks(title="Multi-Agent Stock Analyst") as demo:
    gr.Markdown(
        "# 📈 Multi-Agent Stock Analysis System\n"
        "Four specialist AI agents (technical, news, risk, fundamentals) analyze a stock "
        "in parallel, a supervisor agent synthesizes a recommendation, and an independent "
        "**LLM judge** evaluates whether that recommendation is well-founded.\n\n"
        "*SEN4018 Semester Project — educational demo, not investment advice.*"
    )

    with gr.Row():
        symbol_in = gr.Textbox(label="Stock symbol", placeholder="AAPL, MSFT, NVDA…", scale=3)
        language_in = gr.Radio(["English", "Türkçe"], value="English", label="Language", scale=1)
        analyze_btn = gr.Button("Analyze", variant="primary", scale=1)

    with gr.Row():
        recommendation_out = gr.Markdown(label="Recommendation")
        judge_out = gr.Markdown(label="LLM Judge")

    with gr.Tabs():
        with gr.Tab("Technical"):
            technical_out = gr.Markdown()
        with gr.Tab("News & Sentiment"):
            news_out = gr.Markdown()
        with gr.Tab("Risk"):
            risk_out = gr.Markdown()
        with gr.Tab("Fundamentals"):
            profile_out = gr.Markdown()
        with gr.Tab("Errors"):
            errors_out = gr.Markdown()

    analyze_btn.click(
        run_analysis,
        inputs=[symbol_in, language_in],
        outputs=[
            recommendation_out,
            judge_out,
            technical_out,
            news_out,
            risk_out,
            profile_out,
            errors_out,
        ],
    )

    gr.Examples([["AAPL"], ["MSFT"], ["NVDA"], ["THYAO.IS"]], inputs=[symbol_in])


if __name__ == "__main__":
    demo.launch()
