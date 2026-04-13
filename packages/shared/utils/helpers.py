from datetime import datetime


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
