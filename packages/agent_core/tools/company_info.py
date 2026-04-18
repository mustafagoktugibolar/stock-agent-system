"""Company profile and financial statement tools using yfinance."""

import json
from typing import Any

from langchain_core.tools import tool

from packages.shared.logging.logger import get_logger
from packages.shared.utils.helpers import safe_float

logger = get_logger(__name__)

# Key balance-sheet rows to extract (order matters for readability)
_BALANCE_SHEET_KEYS = [
    "Total Assets",
    "Total Liabilities Net Minority Interest",
    "Stockholders Equity",
    "Total Debt",
    "Cash And Cash Equivalents",
    "Net Debt",
    "Current Assets",
    "Current Liabilities",
    "Total Non Current Assets",
    "Total Non Current Liabilities Net Minority Interest",
]

_INCOME_STATEMENT_KEYS = [
    "Total Revenue",
    "Cost Of Revenue",
    "Gross Profit",
    "Operating Income",
    "Net Income",
    "EBITDA",
    "Basic EPS",
    "Diluted EPS",
    "Total Expenses",
    "Interest Expense",
]

_CASH_FLOW_KEYS = [
    "Operating Cash Flow",
    "Capital Expenditure",
    "Free Cash Flow",
    "Investing Cash Flow",
    "Financing Cash Flow",
    "Repurchase Of Capital Stock",
    "Cash Dividends Paid",
]


def _extract_rows(
    df: Any, keys: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Extract rows from a yfinance financial DataFrame.

    Returns a list of {label, values} dicts and the period column headers.
    """
    if df is None or getattr(df, "empty", True):
        return [], []

    periods = [col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col) for col in df.columns]
    items: list[dict[str, Any]] = []

    for key in keys:
        if key in df.index:
            row = df.loc[key]
            values = {
                period: safe_float(row.iloc[i]) for i, period in enumerate(periods)
            }
            items.append({"label": key, "values": values})

    return items, periods


@tool
def fetch_company_profile(symbol: str) -> str:
    """Fetch company profile information for a stock symbol.

    Returns company name, sector, industry, description, key valuation
    metrics (P/E, market cap, dividend yield, 52-week range), and
    employee count.

    Args:
        symbol: Stock ticker symbol, e.g. 'AAPL', 'MSFT'.

    Returns:
        JSON string with company profile data.
    """
    import yfinance as yf

    symbol = symbol.upper().strip()

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
    except Exception as e:
        logger.error("Failed to fetch company profile for %s: %s", symbol, e)
        return json.dumps({"symbol": symbol, "error": str(e)})

    return json.dumps({
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName", symbol),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "description": info.get("longBusinessSummary"),
        "market_cap": safe_float(info.get("marketCap")),
        "pe_ratio": safe_float(info.get("trailingPE")),
        "forward_pe": safe_float(info.get("forwardPE")),
        "dividend_yield": safe_float(info.get("dividendYield")),
        "fifty_two_week_high": safe_float(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": safe_float(info.get("fiftyTwoWeekLow")),
        "current_price": safe_float(
            info.get("currentPrice") or info.get("regularMarketPrice")
        ),
        "currency": info.get("currency", "USD"),
        "exchange": info.get("exchange"),
        "website": info.get("website"),
        "employees": info.get("fullTimeEmployees"),
    })


@tool
def fetch_financial_statements(symbol: str) -> str:
    """Fetch annual financial statements for a stock symbol.

    Returns key line items from the balance sheet, income statement,
    and cash flow statement (latest 4 annual periods).

    Args:
        symbol: Stock ticker symbol, e.g. 'AAPL', 'MSFT'.

    Returns:
        JSON string with balance_sheet, income_statement, and cash_flow arrays.
    """
    import yfinance as yf

    symbol = symbol.upper().strip()

    try:
        ticker = yf.Ticker(symbol)
        bs = ticker.balance_sheet
        inc = ticker.financials
        cf = ticker.cashflow
    except Exception as e:
        logger.error("Failed to fetch financials for %s: %s", symbol, e)
        return json.dumps({"symbol": symbol, "error": str(e)})

    balance_sheet, bs_periods = _extract_rows(bs, _BALANCE_SHEET_KEYS)
    income_statement, inc_periods = _extract_rows(inc, _INCOME_STATEMENT_KEYS)
    cash_flow, cf_periods = _extract_rows(cf, _CASH_FLOW_KEYS)

    # Use the longest available period list as canonical
    periods = bs_periods or inc_periods or cf_periods

    return json.dumps({
        "symbol": symbol,
        "balance_sheet": balance_sheet,
        "income_statement": income_statement,
        "cash_flow": cash_flow,
        "periods": periods,
    })
