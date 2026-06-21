"""Historical backtest engine — replays the trade decision agent over past data.

Steps day by day through a historical date range. Each trading day it builds an
ObservationOutput from bars available up to that day only (no lookahead), calls
the real trade_decision_agent (same LLM, same prompt as live trading), applies
the same deterministic safety gates, and manages positions against subsequent
daily bars (stop loss / take profit via high-low, time exit at close).

News sentiment is fixed to neutral — historical news is not retrievable — so
decisions are driven by technicals, risk metrics, and regime, which the result
config records explicitly.

One LLM call per symbol per trading day: a 3-month, 1-symbol backtest is ~63
calls. _MAX_LLM_CALLS guards against accidentally huge ranges.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Optional

import httpx

from packages.analysis_agent.tools.indicators import calculate_technical_indicators
from packages.analysis_agent.tools.risk_metrics import calculate_risk_metrics
from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.trading_agent.agents.market_observer_agent import (
    _classify_market_regime,
    _safe_float,
)
from packages.trading_agent.agents.trade_decision_agent import trade_decision_agent
from packages.trading_agent.models.trading_output import ObservationOutput

logger = get_logger(__name__)

_WARMUP_DAYS = 365
_MIN_BARS_FOR_OBSERVATION = 60
_INDICATOR_WINDOW = 250
_MAX_LLM_CALLS = 400


@dataclass
class _SimPosition:
    symbol: str
    quantity: float
    entry_price: float
    entry_date: date
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_confidence: float
    entry_reasoning: str


def _parse_bar_date(timestamp: str) -> date:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()


def _fetch_daily_bars_from_alpaca(symbol: str, start: date, end: date) -> list[dict]:
    """Fetch daily OHLCV bars for [start, end] from Alpaca, oldest first."""
    settings = get_settings()
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        raise ValueError("Alpaca credentials not configured")
    if "." in symbol:
        raise ValueError("Alpaca stock bars do not support dotted non-US symbols")

    url = f"{settings.alpaca_data_url}/v2/stocks/{symbol}/bars"
    headers = {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }
    params: dict[str, Any] = {
        "start": datetime.combine(start, time.min, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Use the next midnight so the requested end date's full daily bar is included.
        "end": datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeframe": "1Day",
        "limit": 10_000,
        "adjustment": "all",
        "feed": "iex",
        "sort": "asc",
    }

    bars: list[dict] = []
    while True:
        response = httpx.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()

        for bar in payload.get("bars", []):
            timestamp = bar["t"]
            bars.append({
                "date": _parse_bar_date(timestamp),
                "timestamp": timestamp,
                "open": float(bar["o"]),
                "high": float(bar["h"]),
                "low": float(bar["l"]),
                "close": float(bar["c"]),
                "volume": int(bar["v"]),
                "source": "alpaca",
            })

        next_page_token = payload.get("next_page_token")
        if not next_page_token:
            break
        params["page_token"] = next_page_token

    if not bars:
        raise ValueError(f"No Alpaca data returned for {symbol}")
    return bars


def _fetch_daily_bars_from_yfinance(symbol: str, start: date, end: date) -> list[dict]:
    """Fetch daily OHLCV bars for [start, end] via yfinance, oldest first."""
    import yfinance as yf

    df = yf.Ticker(symbol).history(
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=True,
    )
    if getattr(df, "empty", True):
        return []

    bars: list[dict] = []
    for ts, row in df.iterrows():
        bars.append({
            "date": ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10]),
            "timestamp": str(ts),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
            "source": "yfinance",
        })
    return bars


def _fetch_daily_bars(symbol: str, start: date, end: date) -> list[dict]:
    """Fetch historical daily bars for [start, end], preferring Alpaca."""
    symbol = symbol.upper().strip()
    try:
        return _fetch_daily_bars_from_alpaca(symbol, start, end)
    except Exception as e:
        logger.warning("[backtest] Alpaca historical fetch failed for %s (%s); falling back to yfinance", symbol, e)
        return _fetch_daily_bars_from_yfinance(symbol, start, end)


def _bars_to_ohlcv_json(symbol: str, bars: list[dict]) -> str:
    return json.dumps({
        "symbol": symbol,
        "source": "backtest",
        "bars": [{k: v for k, v in b.items() if k not in {"date", "source"}} for b in bars],
    })


def _build_observation(
    symbol: str,
    bars: list[dict],
    spy_bars: list[dict],
    as_of: date,
) -> Optional[ObservationOutput]:
    """Build an ObservationOutput from bars up to as_of — mirrors market_observer."""
    if len(bars) < _MIN_BARS_FOR_OBSERVATION:
        return None

    window = bars[-_INDICATOR_WINDOW:]
    ohlcv_json = _bars_to_ohlcv_json(symbol, window)

    current_price = window[-1]["close"]
    prev_close = window[-2]["close"] if len(window) >= 2 else None
    price_change_24h_pct = (
        (current_price - prev_close) / prev_close * 100
        if prev_close and prev_close > 0 else None
    )

    volume_ratio: Optional[float] = None
    recent_volumes = [b["volume"] for b in window[-20:]]
    if len(recent_volumes) >= 2:
        avg_vol = sum(recent_volumes[:-1]) / (len(recent_volumes) - 1)
        if avg_vol > 0:
            volume_ratio = recent_volumes[-1] / avg_vol

    indicators = json.loads(calculate_technical_indicators.invoke({"ohlcv_json": ohlcv_json}))
    if "error" in indicators:
        logger.warning("[backtest] Indicators failed for %s @ %s: %s", symbol, as_of, indicators["error"])
        return None

    rsi = _safe_float(indicators.get("rsi"))
    atr = _safe_float(indicators.get("atr"))
    macd_histogram = _safe_float(indicators.get("macd_histogram"))
    adx = _safe_float(indicators.get("adx"))
    bb_upper = _safe_float(indicators.get("bb_upper"))
    bb_lower = _safe_float(indicators.get("bb_lower"))

    bb_position: Optional[float] = None
    if bb_upper and bb_lower and bb_upper != bb_lower and current_price:
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)

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

    risk_kwargs: dict[str, Any] = {"ohlcv_json": ohlcv_json}
    if spy_bars:
        risk_kwargs["benchmark_json"] = _bars_to_ohlcv_json("SPY", spy_bars[-_INDICATOR_WINDOW:])
    risk_data = json.loads(calculate_risk_metrics.invoke(risk_kwargs))
    risk_level = risk_data.get("risk_level", "medium")
    if risk_level not in ("low", "medium", "high", "very_high"):
        risk_level = "medium"
    annualized_volatility = _safe_float(risk_data.get("annualized_volatility"))

    market_regime = _classify_market_regime(adx, price_change_24h_pct, annualized_volatility)

    return ObservationOutput(
        symbol=symbol,
        timestamp=datetime.combine(as_of, time(16, 0), tzinfo=timezone.utc),
        current_price=current_price,
        price_change_1h_pct=None,
        price_change_24h_pct=price_change_24h_pct,
        volume_ratio=volume_ratio,
        technical_bias=technical_bias,
        rsi=rsi,
        atr=atr,
        macd_histogram=macd_histogram,
        bb_position=bb_position,
        news_sentiment="neutral",
        sentiment_score=0.0,
        risk_level=risk_level,
        annualized_volatility=annualized_volatility,
        market_regime=market_regime,
        signals_json={
            "rsi": rsi,
            "atr": atr,
            "macd_histogram": macd_histogram,
            "adx": adx,
            "bb_position": bb_position,
            "price_change_24h_pct": price_change_24h_pct,
            "volume_ratio": volume_ratio,
        },
    )


def _close_position(
    pos: _SimPosition,
    exit_price: float,
    exit_date: date,
    reason: str,
) -> dict:
    pnl = (exit_price - pos.entry_price) * pos.quantity
    pnl_pct = (exit_price - pos.entry_price) / pos.entry_price * 100 if pos.entry_price > 0 else 0.0
    return {
        "symbol": pos.symbol,
        "quantity": round(pos.quantity, 6),
        "entry_date": pos.entry_date.isoformat(),
        "entry_price": round(pos.entry_price, 4),
        "exit_date": exit_date.isoformat(),
        "exit_price": round(exit_price, 4),
        "exit_reason": reason,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "hold_days": (exit_date - pos.entry_date).days,
        "entry_confidence": pos.entry_confidence,
        "entry_reasoning": pos.entry_reasoning[:300],
    }


def run_backtest(
    symbols: list[str],
    start_date: date,
    end_date: date,
    initial_capital: float = 100_000.0,
    min_confidence: float = 0.55,
    max_position_pct: float = 0.20,
    max_open_positions: int = 5,
    max_hold_days: int = 5,
    progress_cb: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Run a day-stepped historical simulation of the trading agent.

    Returns a result dict with trades, equity curve, and summary stats.
    """
    symbols = [s.upper().strip() for s in symbols if s.strip()]
    if not symbols:
        raise ValueError("At least one symbol is required")
    if end_date <= start_date:
        raise ValueError("end_date must be after start_date")
    if end_date > date.today():
        end_date = date.today()

    bars_by_symbol: dict[str, list[dict]] = {}
    market_data_sources: dict[str, str] = {}
    fetch_start = start_date - timedelta(days=_WARMUP_DAYS)
    for symbol in symbols:
        bars = _fetch_daily_bars(symbol, fetch_start, end_date)
        if not bars:
            raise ValueError(f"No historical data for {symbol}")
        bars_by_symbol[symbol] = bars
        market_data_sources[symbol] = bars[0].get("source", "unknown")
    spy_bars = _fetch_daily_bars("SPY", fetch_start, end_date)
    market_data_sources["SPY"] = spy_bars[0].get("source", "unknown") if spy_bars else "unavailable"

    trading_days = sorted({
        b["date"]
        for bars in bars_by_symbol.values()
        for b in bars
        if start_date <= b["date"] <= end_date
    })
    if not trading_days:
        raise ValueError("No trading days in the selected range")

    estimated_calls = len(trading_days) * len(symbols)
    if estimated_calls > _MAX_LLM_CALLS:
        raise ValueError(
            f"Range too large: ~{estimated_calls} LLM calls (max {_MAX_LLM_CALLS}). "
            f"Use a shorter date range or fewer symbols."
        )

    bar_index: dict[str, dict[date, int]] = {
        symbol: {b["date"]: i for i, b in enumerate(bars)}
        for symbol, bars in bars_by_symbol.items()
    }
    spy_index = {b["date"]: i for i, b in enumerate(spy_bars)}

    cash = initial_capital
    open_positions: dict[str, _SimPosition] = {}
    trades: list[dict] = []
    equity_curve: list[dict] = []
    decisions_log: list[dict] = []
    prev_equity = initial_capital

    def _mark_to_market(day: date) -> float:
        total = cash
        for sym, pos in open_positions.items():
            idx = bar_index[sym].get(day)
            price = bars_by_symbol[sym][idx]["close"] if idx is not None else pos.entry_price
            total += pos.quantity * price
        return total

    for day_num, day in enumerate(trading_days, start=1):
        # ── 1. Manage open positions against today's bar ─────────────────────
        for sym in list(open_positions.keys()):
            idx = bar_index[sym].get(day)
            if idx is None:
                continue
            bar = bars_by_symbol[sym][idx]
            pos = open_positions[sym]

            exit_price: Optional[float] = None
            reason = ""
            if pos.stop_loss and bar["low"] <= pos.stop_loss:
                exit_price, reason = pos.stop_loss, "stop_loss"
            elif pos.take_profit and bar["high"] >= pos.take_profit:
                exit_price, reason = pos.take_profit, "take_profit"
            elif (day - pos.entry_date).days >= max_hold_days:
                exit_price, reason = bar["close"], "time_limit"

            if exit_price is not None:
                trades.append(_close_position(pos, exit_price, day, reason))
                cash += pos.quantity * exit_price
                del open_positions[sym]

        # ── 2. One decision per symbol ────────────────────────────────────────
        for symbol in symbols:
            idx = bar_index[symbol].get(day)
            if idx is None:
                continue

            spy_idx = spy_index.get(day)
            spy_slice = spy_bars[: spy_idx + 1] if spy_idx is not None else []
            observation = _build_observation(
                symbol, bars_by_symbol[symbol][: idx + 1], spy_slice, day,
            )
            if observation is None:
                continue

            equity_now = _mark_to_market(day)
            portfolio_state = {
                "current_equity": round(equity_now, 2),
                "cash": round(cash, 2),
                "buying_power": round(cash, 2),
                "total_open_positions": len(open_positions),
                "open_position_symbols": list(open_positions.keys()),
                "positions": [
                    {"symbol": p.symbol, "qty": p.quantity, "avg_entry_price": p.entry_price, "side": "long"}
                    for p in open_positions.values()
                ],
                "daily_pnl_pct": round((equity_now - prev_equity) / prev_equity * 100, 4) if prev_equity > 0 else 0.0,
                "circuit_breaker_active": False,
                "mode": "backtest",
            }

            result = trade_decision_agent({
                "symbol": symbol,
                "observation": observation,
                "portfolio_state": portfolio_state,
                "retrieved_memories": [],
                "analysis_context": None,
            })
            decision = result.get("trade_decision")
            if decision is None:
                continue

            decisions_log.append({
                "date": day.isoformat(),
                "symbol": symbol,
                "action": decision.action,
                "confidence": decision.confidence,
                "regime": observation.market_regime,
            })

            close_price = bars_by_symbol[symbol][idx]["close"]

            if decision.action == "SELL" and symbol in open_positions:
                pos = open_positions.pop(symbol)
                trades.append(_close_position(pos, close_price, day, "agent_sell"))
                cash += pos.quantity * close_price
                continue

            if decision.action != "BUY":
                continue
            if decision.confidence < min_confidence:
                continue
            if symbol in open_positions:
                continue
            if len(open_positions) >= max_open_positions:
                continue

            max_position_usd = max_position_pct * initial_capital
            capital_to_use = min(decision.position_size_pct * cash, max_position_usd, cash)
            quantity = capital_to_use / close_price if close_price > 0 else 0.0
            if quantity <= 0:
                continue

            cash -= quantity * close_price
            open_positions[symbol] = _SimPosition(
                symbol=symbol,
                quantity=quantity,
                entry_price=close_price,
                entry_date=day,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                entry_confidence=decision.confidence,
                entry_reasoning=decision.reasoning,
            )

        # ── 3. Mark to market ─────────────────────────────────────────────────
        equity = _mark_to_market(day)
        equity_curve.append({"date": day.isoformat(), "equity": round(equity, 2)})
        prev_equity = equity

        if progress_cb:
            progress_cb({
                "day": day_num,
                "total_days": len(trading_days),
                "current_date": day.isoformat(),
                "equity": round(equity, 2),
                "trades_closed": len(trades),
                "open_positions": len(open_positions),
            })

    # ── Close remaining positions at the final close ──────────────────────────
    last_day = trading_days[-1]
    for sym in list(open_positions.keys()):
        pos = open_positions.pop(sym)
        bars = bars_by_symbol[sym]
        idx = bar_index[sym].get(last_day, len(bars) - 1)
        close_price = bars[idx]["close"]
        trades.append(_close_position(pos, close_price, last_day, "end_of_backtest"))
        cash += pos.quantity * close_price

    final_equity = cash
    if equity_curve:
        equity_curve[-1]["equity"] = round(final_equity, 2)

    wins = sum(1 for t in trades if t["pnl"] > 0)
    peak = initial_capital
    max_drawdown_pct = 0.0
    for point in equity_curve:
        peak = max(peak, point["equity"])
        if peak > 0:
            max_drawdown_pct = min(max_drawdown_pct, (point["equity"] - peak) / peak * 100)

    spy_return_pct: Optional[float] = None
    spy_in_range = [b for b in spy_bars if start_date <= b["date"] <= end_date]
    if len(spy_in_range) >= 2 and spy_in_range[0]["close"] > 0:
        spy_return_pct = round(
            (spy_in_range[-1]["close"] - spy_in_range[0]["close"]) / spy_in_range[0]["close"] * 100, 2,
        )

    action_counts: dict[str, int] = {"BUY": 0, "SELL": 0, "HOLD": 0}
    for d in decisions_log:
        action_counts[d["action"]] = action_counts.get(d["action"], 0) + 1

    return {
        "config": {
            "symbols": symbols,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_capital": initial_capital,
            "min_confidence": min_confidence,
            "max_position_pct": max_position_pct,
            "max_open_positions": max_open_positions,
            "max_hold_days": max_hold_days,
            "market_data_sources": market_data_sources,
            "market_data_fetch_start": fetch_start.isoformat(),
            "market_data_fetch_end": end_date.isoformat(),
            "warmup_days": _WARMUP_DAYS,
            "news_sentiment": "fixed_neutral (historical news unavailable)",
        },
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": round((final_equity - initial_capital) / initial_capital * 100, 2),
        "spy_return_pct": spy_return_pct,
        "total_trades": len(trades),
        "winning_trades": wins,
        "win_rate_pct": round(wins / len(trades) * 100, 1) if trades else None,
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "trading_days": len(trading_days),
        "decision_counts": action_counts,
        "trades": trades,
        "equity_curve": equity_curve,
        "decisions": decisions_log,
    }
