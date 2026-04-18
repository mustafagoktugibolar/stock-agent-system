"""Technical analysis agent node."""

import json
from datetime import datetime, timezone
from typing import Any

from packages.agent_core.models.agent_output import TechnicalOutput, TechnicalSignal
from packages.agent_core.state.agent_state import AgentState
from packages.agent_core.tools.indicators import calculate_technical_indicators
from packages.agent_core.tools.market_data import fetch_ohlcv
from packages.shared.logging.logger import get_logger
from packages.shared.utils.helpers import safe_float

logger = get_logger(__name__)


def _signal(indicator: str, value: Any, signal: str, description: str) -> TechnicalSignal:
    return TechnicalSignal(
        indicator=indicator,
        value=safe_float(value, 0.0),
        signal=signal,  # type: ignore[arg-type]
        description=description,
    )


def _support_resistance(ohlcv_json: str) -> tuple[list[float], list[float]]:
    bars = json.loads(ohlcv_json).get("bars", [])[-60:]
    lows = [safe_float(bar.get("low"), 0.0) for bar in bars if bar.get("low") is not None]
    highs = [safe_float(bar.get("high"), 0.0) for bar in bars if bar.get("high") is not None]
    if not lows or not highs:
        return [], []

    recent_lows = lows[-20:] if len(lows) >= 20 else lows
    recent_highs = highs[-20:] if len(highs) >= 20 else highs
    support = sorted({round(min(recent_lows), 2), round(min(lows), 2)})
    resistance = sorted({round(max(recent_highs), 2), round(max(highs), 2)})
    return support, resistance


def technical_agent(state: AgentState) -> dict[str, Any]:
    """LangGraph node: runs technical analysis for the requested symbol.

    Runs the fixed market-data and indicator workflow directly. This avoids
    slow LLM tool-routing loops for a deterministic calculation step.
    """
    symbol = state["symbol"]
    logger.info("[technical_agent] Starting analysis for %s", symbol)

    try:
        ohlcv_json = fetch_ohlcv.invoke(
            {"symbol": symbol, "period": "6mo", "interval": state.get("timeframe", "1d")}
        )
        indicators = json.loads(calculate_technical_indicators.invoke({"ohlcv_json": ohlcv_json}))
        if indicators.get("error"):
            raise ValueError(indicators["error"])
    except Exception as e:
        logger.error("[technical_agent] Technical calculation failed: %s", e)
        return {
            "errors": [f"technical_agent failed: {e}"],
        }

    rsi = indicators.get("rsi")
    macd_histogram = indicators.get("macd_histogram")
    current_price = indicators.get("symbol_price")
    ema20 = indicators.get("ema_20")
    ema50 = indicators.get("ema_50")

    rsi_signal = "neutral"
    if rsi is not None and rsi < 30:
        rsi_signal = "bullish"
    elif rsi is not None and rsi > 70:
        rsi_signal = "bearish"

    macd_signal = "neutral"
    if macd_histogram is not None and macd_histogram > 0:
        macd_signal = "bullish"
    elif macd_histogram is not None and macd_histogram < 0:
        macd_signal = "bearish"

    trend_signal = "neutral"
    if current_price and ema20 and ema50:
        if current_price > ema20 > ema50:
            trend_signal = "bullish"
        elif current_price < ema20 < ema50:
            trend_signal = "bearish"

    signals = [
        _signal("RSI", rsi, rsi_signal, "Momentum based on the latest 14-period RSI."),
        _signal("MACD Histogram", macd_histogram, macd_signal, "MACD momentum spread."),
        _signal("EMA Trend", current_price, trend_signal, "Price position versus EMA 20 and EMA 50."),
    ]

    bullish = sum(1 for item in signals if item.signal == "bullish")
    bearish = sum(1 for item in signals if item.signal == "bearish")
    if bullish > bearish:
        bias = "bullish"
    elif bearish > bullish:
        bias = "bearish"
    else:
        bias = "neutral"

    support, resistance = _support_resistance(ohlcv_json)
    price_change = indicators.get("price_change_pct")
    confidence = min(0.9, 0.55 + (abs(bullish - bearish) * 0.1))
    summary = (
        f"{symbol} technical bias is {bias}. Latest close is "
        f"{safe_float(current_price, 0.0):.2f}"
    )
    if price_change is not None:
        summary += f" with a {safe_float(price_change, 0.0):.2f}% last-bar move."

    technical_output = TechnicalOutput(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        signals=signals,
        overall_technical_bias=bias,  # type: ignore[arg-type]
        support_levels=support,
        resistance_levels=resistance,
        summary=summary,
        confidence=confidence,
    )

    logger.info(
        "[technical_agent] Done for %s - bias=%s confidence=%.2f",
        symbol,
        technical_output.overall_technical_bias,
        technical_output.confidence,
    )
    return {
        "technical_analysis": technical_output,
    }
