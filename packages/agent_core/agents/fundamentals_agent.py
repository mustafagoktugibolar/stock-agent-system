"""Fundamentals agent node — fetches company profile and financial statements."""

import json
from datetime import datetime, timezone
from typing import Any

from packages.agent_core.models.agent_output import (
    CompanyProfile,
    FinancialLineItem,
    FinancialStatements,
)
from packages.agent_core.state.agent_state import AgentState
from packages.agent_core.tools.company_info import (
    fetch_company_profile,
    fetch_financial_statements,
)
from packages.shared.logging.logger import get_logger
from packages.shared.utils.helpers import safe_float

logger = get_logger(__name__)


def _get_value(items: list[dict], label: str, period_index: int = 0) -> float | None:
    """Extract a single value from raw financial statement line items by label."""
    for item in items:
        if item.get("label") == label:
            values = list(item.get("values", {}).values())
            if period_index < len(values):
                return safe_float(values[period_index])
    return None


def _compute_ratios(fin_data: dict) -> dict[str, float | None]:
    """Derive key financial ratios from raw statement line items."""
    bs = fin_data.get("balance_sheet", [])
    inc = fin_data.get("income_statement", [])
    cf = fin_data.get("cash_flow", [])

    revenue0 = _get_value(inc, "Total Revenue", 0)
    revenue1 = _get_value(inc, "Total Revenue", 1)
    gross_profit = _get_value(inc, "Gross Profit", 0)
    net_income0 = _get_value(inc, "Net Income", 0)
    net_income1 = _get_value(inc, "Net Income", 1)
    equity = _get_value(bs, "Stockholders Equity", 0)
    total_assets = _get_value(bs, "Total Assets", 0)
    total_debt = _get_value(bs, "Total Debt", 0)
    current_assets = _get_value(bs, "Current Assets", 0)
    current_liabilities = _get_value(bs, "Current Liabilities", 0)
    free_cash_flow = _get_value(cf, "Free Cash Flow", 0)

    def _ratio(num: float | None, denom: float | None) -> float | None:
        if num is None or denom is None or denom == 0:
            return None
        return round(num / denom, 4)

    def _growth(current: float | None, prior: float | None) -> float | None:
        if current is None or prior is None or prior == 0:
            return None
        return round((current - prior) / abs(prior), 4)

    return {
        "gross_margin": _ratio(gross_profit, revenue0),
        "net_margin": _ratio(net_income0, revenue0),
        "roe": _ratio(net_income0, equity),
        "roa": _ratio(net_income0, total_assets),
        "debt_to_equity": _ratio(total_debt, equity),
        "current_ratio": _ratio(current_assets, current_liabilities),
        "revenue_growth_yoy": _growth(revenue0, revenue1),
        "net_income_growth_yoy": _growth(net_income0, net_income1),
        "fcf_margin": _ratio(free_cash_flow, revenue0),
    }


def fundamentals_agent(state: AgentState) -> dict[str, Any]:
    """LangGraph node: fetches company profile and financial statements.

    Runs deterministic tool calls — no LLM involved.  Provides the
    supervisor with fundamental context about what the company does,
    its valuation, and its balance-sheet health.
    """
    symbol = state["symbol"]
    logger.info("[fundamentals_agent] Starting for %s", symbol)

    result: dict[str, Any] = {}

    # ── Company Profile ───────────────────────────────────────────────────────
    try:
        profile_json = fetch_company_profile.invoke({"symbol": symbol})
        profile_data = json.loads(profile_json)
        if profile_data.get("error"):
            raise ValueError(profile_data["error"])

        result["company_profile"] = CompanyProfile(
            symbol=symbol,
            name=profile_data.get("name", symbol),
            sector=profile_data.get("sector"),
            industry=profile_data.get("industry"),
            description=profile_data.get("description"),
            market_cap=safe_float(profile_data.get("market_cap")),
            pe_ratio=safe_float(profile_data.get("pe_ratio")),
            forward_pe=safe_float(profile_data.get("forward_pe")),
            dividend_yield=safe_float(profile_data.get("dividend_yield")),
            fifty_two_week_high=safe_float(profile_data.get("fifty_two_week_high")),
            fifty_two_week_low=safe_float(profile_data.get("fifty_two_week_low")),
            current_price=safe_float(profile_data.get("current_price")),
            currency=profile_data.get("currency", "USD"),
            exchange=profile_data.get("exchange"),
            website=profile_data.get("website"),
            employees=profile_data.get("employees"),
        )
        logger.info(
            "[fundamentals_agent] Profile loaded for %s — %s (%s)",
            symbol,
            result["company_profile"].name,
            result["company_profile"].sector,
        )
    except Exception as e:
        logger.error("[fundamentals_agent] Profile fetch failed: %s", e)
        result["errors"] = [f"fundamentals_agent profile failed: {e}"]

    # ── Financial Statements ──────────────────────────────────────────────────
    try:
        fin_json = fetch_financial_statements.invoke({"symbol": symbol})
        fin_data = json.loads(fin_json)
        if fin_data.get("error"):
            raise ValueError(fin_data["error"])

        result["financial_statements"] = FinancialStatements(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            balance_sheet=[
                FinancialLineItem(label=item["label"], values=item["values"])
                for item in fin_data.get("balance_sheet", [])
            ],
            income_statement=[
                FinancialLineItem(label=item["label"], values=item["values"])
                for item in fin_data.get("income_statement", [])
            ],
            cash_flow=[
                FinancialLineItem(label=item["label"], values=item["values"])
                for item in fin_data.get("cash_flow", [])
            ],
            periods=fin_data.get("periods", []),
            computed_ratios=_compute_ratios(fin_data),
        )
        logger.info(
            "[fundamentals_agent] Financials loaded for %s — %d periods",
            symbol,
            len(result["financial_statements"].periods),
        )
    except Exception as e:
        logger.error("[fundamentals_agent] Financials fetch failed: %s", e)
        errors = result.get("errors", [])
        errors.append(f"fundamentals_agent financials failed: {e}")
        result["errors"] = errors

    return result
