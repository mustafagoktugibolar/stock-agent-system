"""Analysis fetcher agent — A2A bridge to the analysis pipeline.

LLM-less node. Calls the analysis API cache endpoint for the current symbol.
On cache hit, enriches TradingState with the deep analysis results (supervisor
recommendation, technical signals, news articles, risk metrics) produced by the
analysis agent graph. On cache miss or error, sets analysis_context=None so the
trade_decision_agent falls back to raw observation data only.

Intentional design choices:
- Uses a short timeout (5 s) so a slow analysis API never blocks the trading cycle.
- Never triggers a fresh analysis run — only reads from cache.
- The analysis_api_url is configurable via ANALYSIS_API_URL env var (default: http://localhost:8000).
"""

from __future__ import annotations

from typing import Any

import httpx

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.trading_agent.state.trading_state import TradingState

logger = get_logger(__name__)

_TIMEOUT = 5.0  # seconds — never block the trading cycle


def analysis_fetcher_agent(state: TradingState) -> dict[str, Any]:
    """LangGraph node: fetch cached analysis for state['symbol'] from the analysis API.

    Returns partial TradingState update:
      - analysis_context: dict with keys from AnalysisResponse, or None on miss/error.
    """
    symbol = state["symbol"]
    settings = get_settings()
    url = f"{settings.analysis_api_url}/api/v1/analysis/{symbol}"

    try:
        response = httpx.get(url, timeout=_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            # Only accept completed analyses
            if data.get("status") == "completed":
                logger.info(
                    "[analysis_fetcher] A2A cache hit for %s — recommendation=%s confidence=%.2f",
                    symbol,
                    data.get("recommendation", {}).get("recommendation", "N/A"),
                    data.get("recommendation", {}).get("confidence", 0.0),
                )
                return {
                    "analysis_context": data,
                    "current_agent": "analysis_fetcher",
                }
            else:
                logger.info("[analysis_fetcher] Cache entry for %s not completed (status=%s), skipping", symbol, data.get("status"))
        else:
            logger.info("[analysis_fetcher] Cache miss for %s (HTTP %s)", symbol, response.status_code)
    except httpx.TimeoutException:
        logger.warning("[analysis_fetcher] Timeout fetching analysis for %s — continuing without A2A context", symbol)
    except Exception as e:
        logger.warning("[analysis_fetcher] Failed to fetch analysis for %s: %s", symbol, e)

    return {
        "analysis_context": None,
        "current_agent": "analysis_fetcher",
    }
