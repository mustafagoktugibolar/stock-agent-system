"""News sentiment analysis tool using OpenAI."""

import json

from langchain_core.tools import tool

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


def _uses_reasoning_model(model: str) -> bool:
    """Return True for model families that have stricter chat parameter support."""
    return model.lower().startswith(("gpt-5", "o1", "o3", "o4"))


@tool
def analyze_news_sentiment(news_json: str, symbol: str) -> str:
    """Analyze the sentiment of news articles for a stock using OpenAI.

    Sends all headlines in a single batched request to minimize API calls.

    Args:
        news_json: JSON string returned by the fetch_recent_news tool.
        symbol:    Stock ticker for context (e.g. 'AAPL').

    Returns:
        JSON string with per-article sentiment scores (-1 to +1), an overall
        aggregate score, and a brief summary of key themes.
    """
    from openai import OpenAI

    settings = get_settings()
    data = json.loads(news_json)
    articles = data.get("articles", [])

    if not articles:
        return json.dumps(
            {
                "symbol": symbol,
                "sentiments": [],
                "overall_score": 0.0,
                "overall_label": "neutral",
                "summary": "No news articles available.",
            }
        )

    headlines = "\n".join(
        f"{i + 1}. {a['title']} ({a.get('source', 'unknown')})"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are a financial news sentiment analyst.

Analyze the sentiment of these news headlines for {symbol}.

Headlines:
{headlines}

Instructions:
- Score each headline from -1.0 (very negative) to +1.0 (very positive), 0.0 = neutral.
- Compute an overall aggregate sentiment score (weighted average).
- Identify 2-3 key themes from the headlines.
- Provide a one-sentence summary of the market sentiment implied by this news.

Respond ONLY with valid JSON in this exact format:
{{
  "sentiments": [<score for headline 1>, <score for headline 2>, ...],
  "overall_score": <float>,
  "overall_label": "<positive|neutral|negative>",
  "key_themes": ["<theme1>", "<theme2>"],
  "summary": "<one sentence summary>"
}}"""

    client = OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1)
    request_kwargs = {
        "model": settings.openai_model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "max_completion_tokens": 512,
    }
    if not _uses_reasoning_model(settings.openai_model):
        request_kwargs["temperature"] = 0.1

    try:
        response = client.chat.completions.create(**request_kwargs)
        result = json.loads(response.choices[0].message.content)
        result["symbol"] = symbol
        result["article_count"] = len(articles)
        return json.dumps(result)
    except Exception as e:
        logger.error("Sentiment analysis failed for %s: %s", symbol, e)
        return json.dumps(
            {
                "symbol": symbol,
                "sentiments": [],
                "overall_score": 0.0,
                "overall_label": "neutral",
                "summary": f"Sentiment analysis unavailable: {e}",
                "error": str(e),
            }
        )
