from datetime import datetime
from typing import Any, overload

import numpy as np


@overload
def safe_float(value: Any) -> float | None: ...
@overload
def safe_float(value: Any, default: float) -> float: ...


def safe_float(value: Any, default: float | None = None) -> float | None:
    """Convert *value* to a Python float, handling None / NaN / Inf.

    When *default* is supplied, return it instead of ``None`` for
    unconvertible or missing values.  This satisfies both call-sites:

    * ``safe_float(x)``         → ``float | None``  (tools layer)
    * ``safe_float(x, 0.0)``    → ``float``         (agent layer)
    """
    if value is None:
        return default
    try:
        f = float(value)
        if np.isnan(f) or np.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def format_symbol(symbol: str) -> str:
    """Normalize a stock ticker symbol to uppercase, stripped of whitespace."""
    return symbol.upper().strip()


def round_decimal(value: float, places: int = 2) -> float:
    """Round a float to the given number of decimal places."""
    return round(value, places)


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Divide a by b; return default if b is zero."""
    if b == 0:
        return default
    return a / b


def timestamp_to_str(ts: datetime) -> str:
    """Format a datetime as an ISO 8601 string."""
    return ts.isoformat()


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to the range [lo, hi]."""
    return max(lo, min(hi, value))
