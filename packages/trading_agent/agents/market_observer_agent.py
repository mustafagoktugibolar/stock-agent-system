"""Market observer agent — deterministic observation snapshot (no LLM).

Calls existing tools sequentially to build a complete ObservationOutput for a
single symbol, including market data, technical indicators, news sentiment, risk
metrics, and current portfolio state. Also classifies the market regime using a
deterministic ruleset.
"""

import json
from datetime import datetime, timezone
from typing import Any

from packages.analysis_agent.tools.indicators import calculate_technical_indicators
from packages.analysis_agent.tools.market_data import fetch_ohlcv
from packages.analysis_agent.tools.news_fetcher import fetch_recent_news
from packages.analysis_agent.tools.risk_metrics import calculate_risk_metrics
from packages.analysis_agent.tools.sentiment import analyze_news_sentiment
from packages.shared.logging.logger import get_logger
from packages.trading_agent.models.trading_output import ObservationOutput
from packages.trading_agent.state.trading_state import TradingState
from packages.trading_agent.tools.portfolio_state import get_portfolio_state

logger = get_logger(__name__)


def _classify_market_regime(
    adx: float | None,
    price_change_24h_pct: float | None,
    annualized_volatility: float | None,
) -> str:
    """Deterministic regime classification based on ADX, direction, and volatility."""
    vol = annualized_volatility or 0.0
    adx_val = adx or 0.0
    change = price_change_24h_pct or 0.0

    if vol > 40.0:
        return "high_volatility"
    if adx_val > 25.0 and change > 0:
        return "trending_bull"
    if adx_val > 25.0 and change < 0:
        return "trending_bear"
    return "ranging"


def _safe_float(val: Any, default: float | None = None) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def market_observer_agent(state: TradingState) -> dict[str, Any]:
    """LangGraph node: assembles a full observation snapshot for state['symbol'].

    Purely deterministic — no LLM calls. Reuses all existing analysis_agent tools.
    Returns partial TradingState update with 'observation', 'market_regime',
    and 'portfolio_state' keys.
    """
    symbol = state["symbol"]
    logger.info("[market_observer] Building observation for %s", symbol)

    errors: list[str] = []

    # ── 1. OHLCV (daily 6mo for indicators + risk, hourly 1mo for intraday) ──
    daily_ohlcv_json = fetch_ohlcv.invoke({"symbol": symbol, "period": "6mo", "interval": "1d"})
    hourly_ohlcv_json = fetch_ohlcv.invoke({"symbol": symbol, "period": "1mo", "interval": "1h"})
    spy_ohlcv_json = fetch_ohlcv.invoke({"symbol": "SPY", "period": "1y", "interval": "1d"})

    daily_bars = json.loads(daily_ohlcv_json).get("bars", [])
    hourly_bars = json.loads(hourly_ohlcv_json).get("bars", [])

    # Current and 24h-ago price
    current_price: float = 0.0
    price_change_24h_pct: float | None = None
    price_change_1h_pct: float | None = None
    volume_ratio: float | None = None

    if daily_bars:
        current_price = _safe_float(daily_bars[-1].get("close")) or 0.0
        if len(daily_bars) >= 2:
            prev_close = _safe_float(daily_bars[-2].get("close"))
            if prev_close and prev_close > 0:
                price_change_24h_pct = (current_price - prev_close) / prev_close * 100

        # Volume ratio vs 20-day avg
        recent_volumes = [_safe_float(b.get("volume"), 0.0) for b in daily_bars[-20:]]
        if recent_volumes:
            avg_vol = sum(recent_volumes[:-1]) / max(len(recent_volumes) - 1, 1)
            today_vol = recent_volumes[-1] or 0.0
            if avg_vol > 0:
                volume_ratio = today_vol / avg_vol

    if hourly_bars and len(hourly_bars) >= 2:
        last_close = _safe_float(hourly_bars[-1].get("close")) or 0.0
        prev_close = _safe_float(hourly_bars[-2].get("close"))
        if prev_close and prev_close > 0 and last_close:
            price_change_1h_pct = (last_close - prev_close) / prev_close * 100

    # ── 2. Technical indicators ───────────────────────────────────────────────
    indicators_json = calculate_technical_indicators.invoke({"ohlcv_json": daily_ohlcv_json})
    indicators = json.loads(indicators_json)

    rsi = _safe_float(indicators.get("rsi"))
    atr = _safe_float(indicators.get("atr"))
    macd_histogram = _safe_float(indicators.get("macd_histogram"))
    adx = _safe_float(indicators.get("adx"))
    bb_upper = _safe_float(indicators.get("bb_upper"))
    bb_lower = _safe_float(indicators.get("bb_lower"))

    # Bollinger Band position: 0 = at lower band, 1 = at upper band
    bb_position: float | None = None
    if bb_upper and bb_lower and bb_upper != bb_lower and current_price:
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)

    # Overall technical bias from indicator signals
    bullish_count = 0
    bearish_count = 0
    if rsi is not None:
        if rsi < 40:
            bullish_count += 1
        elif rsi > 60:
            bearish_count += 1
    if macd_histogram is not None:
        if macd_histogram > 0:
            bullish_count += 1
        else:
            bearish_count += 1
    if bb_position is not None:
        if bb_position < 0.3:
            bullish_count += 1
        elif bb_position > 0.7:
            bearish_count += 1

    if bullish_count > bearish_count:
        technical_bias = "bullish"
    elif bearish_count > bullish_count:
        technical_bias = "bearish"
    else:
        technical_bias = "neutral"

    # ── 3. News and sentiment ─────────────────────────────────────────────────
    try:
        news_json = fetch_recent_news.invoke({"symbol": symbol, "max_articles": 10})
        sentiment_json = analyze_news_sentiment.invoke({"news_json": news_json, "symbol": symbol})
        sentiment_data = json.loads(sentiment_json)
        sentiment_score = _safe_float(sentiment_data.get("overall_sentiment_score"), 0.0) or 0.0
        overall_sentiment_str = sentiment_data.get("overall_sentiment", "neutral")
        if overall_sentiment_str not in ("positive", "negative", "neutral"):
            overall_sentiment_str = "neutral"
        news_sentiment = overall_sentiment_str
    except Exception as e:
        logger.warning("[market_observer] News/sentiment failed for %s: %s", symbol, e)
        errors.append(f"news_sentiment_failed: {e}")
        sentiment_score = 0.0
        news_sentiment = "neutral"

    # ── 4. Risk metrics ───────────────────────────────────────────────────────
    risk_json_str = calculate_risk_metrics.invoke({
        "ohlcv_json": daily_ohlcv_json,
        "benchmark_json": spy_ohlcv_json,
    })
    risk_data = json.loads(risk_json_str)
    risk_level_str = risk_data.get("risk_level", "medium")
    if risk_level_str not in ("low", "medium", "high", "very_high"):
        risk_level_str = "medium"
    annualized_volatility = _safe_float(risk_data.get("annualized_volatility"))

    # ── 5. Portfolio state ────────────────────────────────────────────────────
    portfolio_json = get_portfolio_state.invoke({"dummy": ""})
    portfolio_data = json.loads(portfolio_json)

    # ── 6. Market regime (deterministic) ─────────────────────────────────────
    market_regime = _classify_market_regime(adx, price_change_24h_pct, annualized_volatility)

    # ── 7. Assemble signals dict for DB storage ───────────────────────────────
    signals_json = {
        "rsi": rsi,
        "atr": atr,
        "macd_histogram": macd_histogram,
        "adx": adx,
        "bb_position": bb_position,
        "price_change_24h_pct": price_change_24h_pct,
        "price_change_1h_pct": price_change_1h_pct,
        "volume_ratio": volume_ratio,
        "sentiment_score": sentiment_score,
        **{k: v for k, v in indicators.items() if k not in ("rsi", "atr", "macd_histogram", "adx", "bb_upper", "bb_lower")},
    }

    observation = ObservationOutput(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        current_price=current_price,
        price_change_1h_pct=price_change_1h_pct,
        price_change_24h_pct=price_change_24h_pct,
        volume_ratio=volume_ratio,
        technical_bias=technical_bias,
        rsi=rsi,
        atr=atr,
        macd_histogram=macd_histogram,
        bb_position=bb_position,
        news_sentiment=news_sentiment,
        sentiment_score=float(sentiment_score),
        risk_level=risk_level_str,
        annualized_volatility=annualized_volatility,
        portfolio_state_json=portfolio_data,
        similar_memories=[],
        market_regime=market_regime,
        signals_json=signals_json,
    )

    logger.info(
        "[market_observer] %s: price=%.2f regime=%s bias=%s rsi=%s",
        symbol, current_price, market_regime, technical_bias, rsi,
    )

    result: dict[str, Any] = {
        "observation": observation,
        "market_regime": market_regime,
        "portfolio_state": portfolio_data,
        "current_agent": "market_observer",
    }
    if errors:
        result["errors"] = errors
    return result
