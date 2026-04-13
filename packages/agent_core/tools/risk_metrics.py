"""Risk metrics calculation tool."""

import json
from typing import Any

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_RISK_FREE_RATE_ANNUAL = 0.045  # 4.5% annualized


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        return None if np.isnan(f) or np.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _ohlcv_to_returns(ohlcv_json: str) -> pd.Series:
    data = json.loads(ohlcv_json)
    bars = data.get("bars", data)
    df = pd.DataFrame(bars)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df.dropna(subset=["close"], inplace=True)
    return df["close"].pct_change().dropna()


@tool
def calculate_risk_metrics(ohlcv_json: str, benchmark_json: str = "") -> str:
    """Calculate risk metrics for a stock from OHLCV data.

    Computes annualized volatility, Value-at-Risk (95%), max drawdown,
    Sharpe ratio, and optionally beta vs a benchmark (e.g. SPY).

    Args:
        ohlcv_json:    JSON string from the fetch_ohlcv tool (for the target symbol).
        benchmark_json: Optional JSON string from fetch_ohlcv for the benchmark (SPY).
                        Pass an empty string to skip beta calculation.

    Returns:
        JSON string with risk metric values and interpretations.
    """
    try:
        returns = _ohlcv_to_returns(ohlcv_json)
    except Exception as e:
        return json.dumps({"error": f"Failed to parse OHLCV data: {e}"})

    if len(returns) < 20:
        return json.dumps({"error": "Insufficient data for risk calculation (need ≥20 bars)"})

    # ── Annualized Volatility ─────────────────────────────────────────────────
    ann_volatility = _safe_float(returns.std() * np.sqrt(252))

    # ── Value-at-Risk (95% confidence, daily) ────────────────────────────────
    var_95 = _safe_float(np.percentile(returns, 5))

    # ── Max Drawdown ─────────────────────────────────────────────────────────
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown_series = (cumulative - rolling_max) / rolling_max
    max_drawdown = _safe_float(drawdown_series.min())

    # ── Sharpe Ratio (annualized) ─────────────────────────────────────────────
    rf_daily = _RISK_FREE_RATE_ANNUAL / 252
    sharpe = _safe_float(
        (returns.mean() - rf_daily) / returns.std() * np.sqrt(252)
        if returns.std() > 0
        else None
    )

    # ── Beta vs Benchmark ─────────────────────────────────────────────────────
    beta = None
    if benchmark_json:
        try:
            bench_returns = _ohlcv_to_returns(benchmark_json)
            aligned = pd.concat([returns, bench_returns], axis=1).dropna()
            if len(aligned) >= 20:
                cov_matrix = aligned.cov()
                bench_var = float(bench_returns.var())
                if bench_var > 0:
                    beta = _safe_float(cov_matrix.iloc[0, 1] / bench_var)
        except Exception as e:
            logger.warning("Beta calculation failed: %s", e)

    # ── 30-day return ─────────────────────────────────────────────────────────
    returns_30d = _safe_float(returns.tail(30).sum())

    # ── Calmar Ratio ─────────────────────────────────────────────────────────
    calmar = None
    if ann_volatility and max_drawdown and max_drawdown != 0:
        annual_return = _safe_float(returns.mean() * 252)
        if annual_return is not None:
            calmar = _safe_float(annual_return / abs(max_drawdown))

    return json.dumps(
        {
            "annualized_volatility": ann_volatility,
            "var_95_daily": var_95,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "calmar_ratio": calmar,
            "beta": beta,
            "returns_30d": returns_30d,
            "data_points": len(returns),
        }
    )
