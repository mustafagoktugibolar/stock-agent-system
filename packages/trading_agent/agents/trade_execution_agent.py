"""Trade execution agent — deterministic order placement with safety gates.

No LLM. Runs sequential safety gate checks, then calls the Alpaca trading tool
to submit the order. All gate-failure reasons are recorded in the output so the
reflection system can account for skipped trades.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.trading_agent.models.trading_output import TradeExecutionOutput
from packages.trading_agent.state.trading_state import TradingState
from packages.trading_agent.tools.alpaca_trading import place_order

logger = get_logger(__name__)


def _count_open_positions_for_symbol(symbol: str, portfolio: dict) -> int:
    positions = portfolio.get("positions", [])
    return sum(1 for p in positions if p.get("symbol") == symbol)


def trade_execution_agent(state: TradingState) -> dict[str, Any]:
    """LangGraph node: applies safety gates and submits order to Alpaca.

    Safety gate sequence (all deterministic, enforced in code):
      1. TRADING_ENABLED=false → skip
      2. action == HOLD → skip
      3. circuit_breaker_active → skip
      4. open positions >= MAX_OPEN_POSITIONS → skip
      5. symbol already has open position (no pyramiding on BUY) → skip
      6. confidence < MIN_DECISION_CONFIDENCE → skip
      7. Compute quantity; clamp to MAX_POSITION_SIZE_USD
      8. Submit order via Alpaca SDK
    """
    symbol = state["symbol"]
    decision = state.get("trade_decision")
    portfolio = state.get("portfolio_state") or {}
    settings = get_settings()
    now = datetime.now(timezone.utc)

    def _skip(reason: str) -> dict[str, Any]:
        logger.info("[trade_execution] %s: skipping — %s", symbol, reason)
        output = TradeExecutionOutput(
            symbol=symbol,
            timestamp=now,
            order_submitted=False,
            status="skipped",
            skipped_reason=reason,
        )
        return {"execution_result": output, "current_agent": "trade_execution"}

    # Gate 1: master kill switch
    if not settings.trading_enabled:
        return _skip("TRADING_ENABLED=false")

    # Gate 2: HOLD action
    if decision is None or decision.action == "HOLD":
        return _skip("HOLD action")

    # Gate 3: circuit breaker
    if portfolio.get("circuit_breaker_active", False):
        return _skip("circuit_breaker_active")

    # Gate 4: max open positions
    total_open = portfolio.get("total_open_positions", 0)
    if total_open >= settings.max_open_positions:
        return _skip(f"max_positions_reached ({total_open}/{settings.max_open_positions})")

    # Gate 5: no pyramiding (skip BUY if symbol already open)
    if decision.action == "BUY" and _count_open_positions_for_symbol(symbol, portfolio) > 0:
        return _skip(f"symbol_already_open ({symbol})")

    # Gate 6: minimum confidence threshold
    if decision.confidence < settings.min_decision_confidence:
        return _skip(
            f"low_confidence ({decision.confidence:.2f} < {settings.min_decision_confidence:.2f})"
        )

    # Gate 7: compute order quantity
    available_cash = float(portfolio.get("cash", 0.0))
    current_price = float(state.get("observation").current_price) if state.get("observation") else 0.0

    if current_price <= 0:
        return _skip("invalid_current_price")

    raw_value = decision.position_size_pct * available_cash
    clamped_value = min(raw_value, settings.max_position_size_usd)
    if clamped_value != raw_value:
        logger.info(
            "[trade_execution] %s: position clamped from $%.2f to $%.2f (MAX_POSITION_SIZE_USD)",
            symbol, raw_value, clamped_value,
        )

    quantity = round(clamped_value / current_price, 6)
    if quantity <= 0:
        return _skip("computed_quantity_zero")

    side = "buy" if decision.action == "BUY" else "sell"

    # Gate 8: submit order
    logger.info(
        "[trade_execution] %s: placing %s order qty=%.6f price=~%.4f",
        symbol, side, quantity, current_price,
    )

    order_result_json = place_order.invoke({
        "symbol": symbol,
        "side": side,
        "qty": quantity,
        "order_type": decision.entry_price_type,
        "limit_price": decision.limit_price,
        "stop_loss": decision.stop_loss,
        "take_profit": decision.take_profit,
    })
    order_result = json.loads(order_result_json)

    if "error" in order_result:
        logger.error("[trade_execution] Alpaca order failed for %s: %s", symbol, order_result["error"])
        output = TradeExecutionOutput(
            symbol=symbol,
            timestamp=now,
            order_submitted=False,
            status="error",
            error=order_result["error"],
            order_type=decision.entry_price_type,
        )
        return {
            "execution_result": output,
            "current_agent": "trade_execution",
            "errors": [f"order_failed: {order_result['error']}"],
        }

    output = TradeExecutionOutput(
        symbol=symbol,
        timestamp=now,
        order_submitted=True,
        alpaca_order_id=order_result.get("alpaca_order_id"),
        side=side,
        quantity=quantity,
        order_type=decision.entry_price_type,
        status=order_result.get("status", "submitted"),
    )

    logger.info(
        "[trade_execution] %s: order submitted alpaca_id=%s status=%s",
        symbol, output.alpaca_order_id, output.status,
    )
    return {"execution_result": output, "current_agent": "trade_execution"}
