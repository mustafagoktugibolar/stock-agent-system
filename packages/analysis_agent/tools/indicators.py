"""Technical indicators tool using pandas-ta."""

import json
from typing import Any

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from packages.shared.logging.logger import get_logger
from packages.shared.utils.helpers import safe_float

logger = get_logger(__name__)


def _ohlcv_to_df(ohlcv_json: str) -> pd.DataFrame:
    data = json.loads(ohlcv_json)
    bars = data.get("bars", data)  # accept both wrapped and raw list
    df = pd.DataFrame(bars)
    df.rename(
        columns={
            "timestamp": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        },
        inplace=True,
    )
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df.set_index("date", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df.sort_index(inplace=True)
    return df


@tool
def calculate_technical_indicators(ohlcv_json: str) -> str:
    """Calculate technical indicators from OHLCV market data.

    Computes RSI, MACD, Bollinger Bands, ADX, ATR, and EMAs (20/50/200)
    using the pandas-ta library.

    Args:
        ohlcv_json: JSON string returned by the fetch_ohlcv tool.

    Returns:
        JSON string with the latest indicator values plus current price info.
    """
    import pandas_ta as ta  # noqa: F401 — activates DataFrame extension

    df = _ohlcv_to_df(ohlcv_json)

    if len(df) < 30:
        return json.dumps({"error": "Insufficient data for indicator calculation"})

    # ── Individual indicators ──────────────────────────────────────────────────
    rsi = df.ta.rsi(length=14)
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    bb = df.ta.bbands(length=20, std=2.0)
    adx = df.ta.adx(length=14)
    atr = df.ta.atr(length=14)
    ema20 = df.ta.ema(length=20)
    ema50 = df.ta.ema(length=50)
    ema200 = df.ta.ema(length=200) if len(df) >= 200 else None

    # ── Extract latest values ──────────────────────────────────────────────────
    current_price = safe_float(df["close"].iloc[-1])
    prev_close = safe_float(df["close"].iloc[-2]) if len(df) >= 2 else None
    price_change_pct = (
        round((current_price - prev_close) / prev_close * 100, 2)
        if current_price and prev_close
        else None
    )

    result: dict[str, Any] = {
        "symbol_price": current_price,
        "price_change_pct": price_change_pct,
        "data_points": len(df),
        # RSI
        "rsi": safe_float(rsi.iloc[-1]) if rsi is not None else None,
        # MACD
        "macd_line": None,
        "macd_signal": None,
        "macd_histogram": None,
        # Bollinger Bands
        "bb_upper": None,
        "bb_middle": None,
        "bb_lower": None,
        "bb_bandwidth": None,
        # ADX
        "adx": None,
        "adx_pos_di": None,
        "adx_neg_di": None,
        # ATR
        "atr": None,
        # EMAs
        "ema_20": safe_float(ema20.iloc[-1]) if ema20 is not None else None,
        "ema_50": safe_float(ema50.iloc[-1]) if ema50 is not None else None,
        "ema_200": safe_float(ema200.iloc[-1]) if ema200 is not None else None,
    }

    if macd is not None:
        for col in macd.columns:
            col_lower = col.lower()
            if "macd_" in col_lower and "macds" not in col_lower and "macdh" not in col_lower:
                result["macd_line"] = safe_float(macd[col].iloc[-1])
            elif "macds" in col_lower:
                result["macd_signal"] = safe_float(macd[col].iloc[-1])
            elif "macdh" in col_lower:
                result["macd_histogram"] = safe_float(macd[col].iloc[-1])

    if bb is not None:
        for col in bb.columns:
            col_lower = col.lower()
            if col_lower.startswith("bbu"):
                result["bb_upper"] = safe_float(bb[col].iloc[-1])
            elif col_lower.startswith("bbm"):
                result["bb_middle"] = safe_float(bb[col].iloc[-1])
            elif col_lower.startswith("bbl"):
                result["bb_lower"] = safe_float(bb[col].iloc[-1])
            elif col_lower.startswith("bbb"):
                result["bb_bandwidth"] = safe_float(bb[col].iloc[-1])

    if adx is not None:
        for col in adx.columns:
            col_lower = col.lower()
            if col_lower.startswith("adx_"):
                result["adx"] = safe_float(adx[col].iloc[-1])
            elif "dmp" in col_lower:
                result["adx_pos_di"] = safe_float(adx[col].iloc[-1])
            elif "dmn" in col_lower:
                result["adx_neg_di"] = safe_float(adx[col].iloc[-1])

    if atr is not None:
        result["atr"] = safe_float(atr.iloc[-1])

    return json.dumps(result)
