"""Risk management agent node."""

import json
from datetime import datetime, timezone
from typing import Any

from packages.agent_core.models.agent_output import RiskMetric, RiskOutput
from packages.agent_core.state.agent_state import AgentState
from packages.agent_core.tools.market_data import fetch_ohlcv
from packages.agent_core.tools.risk_metrics import calculate_risk_metrics
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _classify_risk(volatility: float, max_drawdown: float, beta: float | None) -> str:
    if volatility < 0.15:
        level = "low"
    elif volatility < 0.25:
        level = "medium"
    elif volatility < 0.40:
        level = "high"
    else:
        level = "very_high"

    if abs(max_drawdown) > 0.30 and level in {"low", "medium"}:
        level = "high"
    if beta is not None and beta > 1.5 and level != "very_high":
        level = "high"
    return level


def _volatility_percentile(volatility: float) -> float:
    if volatility < 0.15:
        return 20.0
    if volatility < 0.25:
        return 50.0
    if volatility < 0.40:
        return 75.0
    return 90.0


def risk_agent(state: AgentState) -> dict[str, Any]:
    """LangGraph node: evaluates the risk profile for the requested symbol.

    Fetches one year of data for both the symbol and SPY benchmark, then
    computes risk metrics directly.
    """
    symbol = state["symbol"]
    logger.info("[risk_agent] Starting analysis for %s", symbol)

    try:
        ohlcv_json = fetch_ohlcv.invoke({"symbol": symbol, "period": "1y", "interval": "1d"})
        benchmark_json = fetch_ohlcv.invoke({"symbol": "SPY", "period": "1y", "interval": "1d"})
        metrics_data = json.loads(
            calculate_risk_metrics.invoke(
                {"ohlcv_json": ohlcv_json, "benchmark_json": benchmark_json}
            )
        )
        if metrics_data.get("error"):
            raise ValueError(metrics_data["error"])
    except Exception as e:
        logger.error("[risk_agent] Risk calculation failed: %s", e)
        return {
            "errors": [f"risk_agent failed: {e}"],
        }

    volatility = _safe_float(metrics_data.get("annualized_volatility"))
    max_drawdown = _safe_float(metrics_data.get("max_drawdown"))
    beta = metrics_data.get("beta")
    beta_value = float(beta) if beta is not None else None
    risk_level = _classify_risk(volatility, max_drawdown, beta_value)

    metrics = [
        RiskMetric(
            metric_name="Annualized Volatility",
            value=volatility,
            interpretation="Expected annualized price variability based on daily returns.",
        ),
        RiskMetric(
            metric_name="Daily VaR 95%",
            value=_safe_float(metrics_data.get("var_95_daily")),
            interpretation="Estimated one-day downside at the 95% confidence level.",
        ),
        RiskMetric(
            metric_name="Maximum Drawdown",
            value=max_drawdown,
            interpretation="Worst peak-to-trough decline in the lookback window.",
        ),
        RiskMetric(
            metric_name="Sharpe Ratio",
            value=_safe_float(metrics_data.get("sharpe_ratio")),
            interpretation="Risk-adjusted return relative to the configured risk-free rate.",
        ),
        RiskMetric(
            metric_name="30-day Return",
            value=_safe_float(metrics_data.get("returns_30d")),
            interpretation="Recent cumulative return over the latest 30 trading sessions.",
        ),
    ]
    if beta_value is not None:
        metrics.append(
            RiskMetric(
                metric_name="Beta vs SPY",
                value=beta_value,
                interpretation="Sensitivity to broad US market movement.",
            )
        )

    summary = (
        f"{symbol} risk is classified as {risk_level}. "
        f"Annualized volatility is {volatility:.1%} and max drawdown is {max_drawdown:.1%}."
    )
    risk_output = RiskOutput(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        metrics=metrics,
        risk_level=risk_level,  # type: ignore[arg-type]
        volatility_percentile=_volatility_percentile(volatility),
        max_drawdown=max_drawdown,
        beta=beta_value,
        summary=summary,
        confidence=0.8 if beta_value is not None else 0.65,
    )

    logger.info(
        "[risk_agent] Done for %s - risk_level=%s confidence=%.2f",
        symbol,
        risk_output.risk_level,
        risk_output.confidence,
    )
    return {
        "risk_analysis": risk_output,
    }
