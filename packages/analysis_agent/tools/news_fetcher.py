"""News fetching tool using Yahoo Finance (yfinance)."""

import json
from datetime import datetime, timezone

from langchain_core.tools import tool

from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


@tool
def fetch_recent_news(symbol: str, max_articles: int = 10) -> str:
    """Fetch recent news articles for a stock symbol using Yahoo Finance.

    Args:
        symbol:       Stock ticker symbol, e.g. 'AAPL'.
        max_articles: Maximum number of articles to return (1–20).

    Returns:
        JSON string with a list of news article objects, each containing:
        title, source, url, and published_at (ISO timestamp or null).
    """
    import yfinance as yf

    symbol = symbol.upper().strip()
    max_articles = max(1, min(20, max_articles))

    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news or []
    except Exception as e:
        logger.error("Failed to fetch news for %s: %s", symbol, e)
        return json.dumps({"symbol": symbol, "articles": [], "error": str(e)})

    articles = []
    for item in raw_news[:max_articles]:
        # yfinance has used both a flat shape and a nested "content" shape.
        content = item.get("content", item)
        pub_ts = item.get("providerPublishTime") or content.get("providerPublishTime")
        published_at = None
        if pub_ts:
            try:
                published_at = datetime.fromtimestamp(pub_ts, tz=timezone.utc).isoformat()
            except (OSError, OverflowError, ValueError):
                published_at = None
        elif content.get("pubDate"):
            published_at = content.get("pubDate")

        provider = content.get("provider") or {}
        canonical_url = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}

        articles.append(
            {
                "title": item.get("title") or content.get("title", ""),
                "source": item.get("publisher") or provider.get("displayName", ""),
                "url": item.get("link") or canonical_url.get("url", ""),
                "published_at": published_at,
                "summary": content.get("summary") or content.get("description", ""),
            }
        )

    return json.dumps({"symbol": symbol, "articles": articles})
