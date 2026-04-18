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
