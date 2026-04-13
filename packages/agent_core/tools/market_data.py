"""Market data fetching tool.

Primary source: Alpaca Markets Data API.
Fallback:       yfinance (Yahoo Finance, no API key required).
"""

import json
from typing import Any, Dict, List
from datetime import datetime, timedelta, timezone

import httpx
from langchain_core.tools import tool

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_PERIOD_TO_DAYS = {
    "1mo": 30,
    "3mo": 90,
    "6mo": 180,
    "1y": 365,
    "2y": 730,
}


def _fetch_from_alpaca(symbol: str, period: str, interval: str) -> str:
    settings = get_settings()
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        raise ValueError("Alpaca credentials not configured")

    days = _PERIOD_TO_DAYS.get(period, 90)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    # Map interval to Alpaca timeframe
    timeframe_map = {"1d": "1Day", "1h": "1Hour", "5m": "5Min"}
    timeframe = timeframe_map.get(interval, "1Day")

    url = f"{settings.alpaca_data_url}/v2/stocks/{symbol}/bars"
    headers = {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }
    params: Dict[str, Any] = {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeframe": timeframe,
        "limit": 1000,
        "adjustment": "all",
        "feed": "iex",
    }

    # Reduce timeout to avoid long blocking waits when Alpaca is slow.
    response: httpx.Response = httpx.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    bars: List[Dict[str, Any]] = response.json().get("bars", [])
    if not bars:
        raise ValueError(f"No Alpaca data returned for {symbol}")

    records: List[Dict[str, Any]] = [
        {
            "timestamp": bar["t"],
            "open": bar["o"],
            "high": bar["h"],
            "low": bar["l"],
            "close": bar["c"],
            "volume": bar["v"],
        }
        for bar in bars
    ]
    return json.dumps({"symbol": symbol, "source": "alpaca", "bars": records})


def _fetch_from_yfinance(symbol: str, period: str, interval: str) -> str:
    import yfinance as yf

    ticker: Any = yf.Ticker(symbol)
    df: Any = ticker.history(period=period, interval=interval, auto_adjust=True)

    if getattr(df, "empty", False):
        raise ValueError(f"No yfinance data returned for {symbol}")

    df.index = df.index.astype(str)
    records: List[Dict[str, Any]] = [
        {
            "timestamp": str(ts),
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "volume": int(row["Volume"]),
        }
        for ts, row in df.iterrows()
    ]
    return json.dumps({"symbol": symbol, "source": "yfinance", "bars": records})


@tool  # type: ignore
def fetch_ohlcv(symbol: str, period: str = "3mo", interval: str = "1d") -> str:
    """Fetch OHLCV (Open, High, Low, Close, Volume) market data for a stock symbol.

    Args:
        symbol:   Stock ticker symbol, e.g. 'AAPL', 'MSFT', 'SPY'.
        period:   Lookback period — one of '1mo', '3mo', '6mo', '1y', '2y'.
        interval: Bar interval — one of '1d' (daily), '1h' (hourly), '5m' (5-minute).

    Returns:
        JSON string with keys 'symbol', 'source', and 'bars' (list of OHLCV dicts).
    """
    symbol = symbol.upper().strip()
    if "." in symbol:
        logger.info("Symbol %s looks non-US (contains '.'), using yfinance fallback", symbol)
        return _fetch_from_yfinance(symbol, period, interval)

    try:
        return _fetch_from_alpaca(symbol, period, interval)
    except Exception as e:
        logger.warning("Alpaca fetch failed for %s (%s), falling back to yfinance", symbol, e)
        return _fetch_from_yfinance(symbol, period, interval)
