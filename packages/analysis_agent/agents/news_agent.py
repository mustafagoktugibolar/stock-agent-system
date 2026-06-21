"""News & sentiment analysis agent node."""

import json
from datetime import datetime, timezone
from typing import Any

from packages.analysis_agent.models.agent_output import NewsItem, NewsOutput
from packages.analysis_agent.state.agent_state import AgentState
from packages.analysis_agent.tools.news_fetcher import fetch_recent_news
from packages.analysis_agent.tools.sentiment import analyze_news_sentiment
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


def news_agent(state: AgentState) -> dict[str, Any]:
    """LangGraph node: fetches news and runs sentiment analysis for the symbol.

    Runs the fixed news and sentiment workflow directly to avoid slow LLM
    tool-routing loops.
    """
    symbol = state["symbol"]
    logger.info("[news_agent] Starting analysis for %s", symbol)

    try:
        news_json = fetch_recent_news.invoke({"symbol": symbol, "max_articles": 10})
        news_data = json.loads(news_json)
        sentiment_json = analyze_news_sentiment.invoke({"news_json": news_json, "symbol": symbol})
        sentiment_data = json.loads(sentiment_json)
    except Exception as e:
        logger.error("[news_agent] News analysis failed: %s", e)
        return {
            "errors": [f"news_agent failed: {e}"],
        }

    articles = news_data.get("articles", [])
    scores = sentiment_data.get("sentiments", [])
    news_items = [
        NewsItem(
            title=article.get("title", ""),
            source=article.get("source", ""),
            published_at=article.get("published_at"),
            sentiment_score=float(scores[index]) if index < len(scores) else 0.0,
            summary=article.get("summary") or "Headline sentiment analysis.",
        )
        for index, article in enumerate(articles)
    ]

    score = float(sentiment_data.get("overall_score", 0.0) or 0.0)
    label = sentiment_data.get("overall_label")
    if label not in {"positive", "negative", "neutral"}:
        label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"

    n = len(news_items)
    if not sentiment_data.get("error"):
        confidence = min(0.85, 0.45 + n * 0.04)
    else:
        confidence = min(0.55, 0.30 + n * 0.03)
    news_output = NewsOutput(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        news_items=news_items,
        overall_sentiment=label,
        sentiment_score=max(-1.0, min(1.0, score)),
        summary=sentiment_data.get("summary", "No news sentiment summary available."),
        confidence=confidence,
    )

    logger.info(
        "[news_agent] Done for %s - sentiment=%s score=%.2f confidence=%.2f",
        symbol,
        news_output.overall_sentiment,
        news_output.sentiment_score,
        news_output.confidence,
    )
    return {
        "news_analysis": news_output,
    }
