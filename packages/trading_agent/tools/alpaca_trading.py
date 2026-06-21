"""Alpaca paper trading API tools.

All functions are synchronous LangChain @tool wrappers, consistent with the
existing tool pattern in packages/analysis_agent/tools/. Uses the alpaca-py SDK
(TradingClient) with paper=True.
"""

import json
from typing import Optional

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import (
    LimitOrderRequest,
    MarketOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from langchain_core.tools import tool

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_trading_client: Optional[TradingClient] = None


def _get_trading_client() -> TradingClient:
    global _trading_client
    if _trading_client is None:
        settings = get_settings()
        _trading_client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=True,
        )
    return _trading_client


@tool
def get_account_info(dummy: str = "") -> str:
    """Get Alpaca paper trading account summary including equity, cash, and buying power."""
    try:
        account = _get_trading_client().get_account()
        return json.dumps({
            "equity": float(account.equity),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "daytrade_count": account.daytrade_count,
            "daytrading_buying_power": float(account.daytrading_buying_power) if account.daytrading_buying_power else None,
            "currency": account.currency,
        })
    except APIError as e:
        logger.error("get_account_info failed: %s", e)
        return json.dumps({"error": str(e)})


@tool
def get_open_positions(dummy: str = "") -> str:
    """Get all currently open positions in the paper trading account."""
    try:
        positions = _get_trading_client().get_all_positions()
        result = []
        for pos in positions:
            result.append({
                "symbol": pos.symbol,
                "qty": float(pos.qty),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price) if pos.current_price else None,
                "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else None,
                "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else None,
                "side": pos.side.value if pos.side else None,
                "market_value": float(pos.market_value) if pos.market_value else None,
            })
        return json.dumps(result)
    except APIError as e:
        logger.error("get_open_positions failed: %s", e)
        return json.dumps({"error": str(e)})


@tool
def place_order(
    symbol: str,
    side: str,
    qty: float,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
) -> str:
    """Place a paper trading order on Alpaca.

    Args:
        symbol: Ticker symbol (e.g. "AAPL")
        side: "buy" or "sell"
        qty: Number of shares (fractional supported)
        order_type: "market" or "limit"
        limit_price: Required for limit orders
        stop_loss: Optional stop-loss price (creates bracket order when combined with take_profit)
        take_profit: Optional take-profit price (creates bracket order when combined with stop_loss)
    """
    try:
        client = _get_trading_client()
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        take_profit_req = TakeProfitRequest(limit_price=take_profit) if take_profit else None
        stop_loss_req = StopLossRequest(stop_price=stop_loss) if stop_loss else None

        if order_type == "limit" and limit_price is not None:
            request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price,
                take_profit=take_profit_req,
                stop_loss=stop_loss_req,
            )
        else:
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                take_profit=take_profit_req,
                stop_loss=stop_loss_req,
            )

        order = client.submit_order(request)
        return json.dumps({
            "alpaca_order_id": str(order.id),
            "symbol": order.symbol,
            "side": order.side.value,
            "qty": float(order.qty) if order.qty else None,
            "order_type": order.order_type.value,
            "status": order.status.value,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        })
    except APIError as e:
        logger.error("place_order failed for %s: %s", symbol, e)
        return json.dumps({"error": str(e), "symbol": symbol})


@tool
def close_position(symbol: str, percentage: float = 100.0) -> str:
    """Close an open position for a symbol. percentage=100.0 closes the full position."""
    try:
        client = _get_trading_client()
        if percentage >= 100.0:
            order = client.close_position(symbol)
        else:
            # partial close via percentage
            order = client.close_position(symbol, percentage=percentage)
        return json.dumps({
            "alpaca_order_id": str(order.id),
            "symbol": order.symbol,
            "side": order.side.value,
            "status": order.status.value,
        })
    except APIError as e:
        logger.error("close_position failed for %s: %s", symbol, e)
        return json.dumps({"error": str(e), "symbol": symbol})


@tool
def get_portfolio_history(period: str = "1D", timeframe: str = "5Min") -> str:
    """Get portfolio equity history for PnL tracking.

    Args:
        period: Time period e.g. "1D", "1W", "1M"
        timeframe: Bar size e.g. "5Min", "15Min", "1H"
    """
    try:
        history = _get_trading_client().get_portfolio_history(
            period=period,
            timeframe=timeframe,
        )
        return json.dumps({
            "equity": [float(v) for v in history.equity] if history.equity else [],
            "profit_loss": [float(v) for v in history.profit_loss] if history.profit_loss else [],
            "profit_loss_pct": [float(v) for v in history.profit_loss_pct] if history.profit_loss_pct else [],
            "timestamp": history.timestamp if history.timestamp else [],
        })
    except APIError as e:
        logger.error("get_portfolio_history failed: %s", e)
        return json.dumps({"error": str(e)})


@tool
def get_order_status(alpaca_order_id: str) -> str:
    """Get the current status of an Alpaca order by its ID."""
    try:
        order = _get_trading_client().get_order_by_id(alpaca_order_id)
        return json.dumps({
            "alpaca_order_id": str(order.id),
            "symbol": order.symbol,
            "status": order.status.value,
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            "filled_qty": float(order.filled_qty) if order.filled_qty else None,
            "filled_at": order.filled_at.isoformat() if order.filled_at else None,
        })
    except APIError as e:
        logger.error("get_order_status failed for %s: %s", alpaca_order_id, e)
        return json.dumps({"error": str(e)})
