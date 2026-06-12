"""Trading cycle StateGraph — Observe → Memory → Decide → [Execute] → Persist.

Runs every 30 minutes during market hours for each symbol in the watchlist.
The conditional edge 'should_execute' enforces all safety gates at the graph
level; the TradeExecutionAgent has its own redundant gate checks.
"""

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import psycopg2
import psycopg2.extras
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select, text

from packages.shared.config.settings import get_settings
from packages.shared.db.models.trading import (
    TradeDecision,
    TradeOrder,
    TradePosition,
    TradingSession,
)
from packages.shared.db.session import get_session_factory
from packages.shared.logging.logger import get_logger
from packages.trading_agent.agents.analysis_fetcher_agent import analysis_fetcher_agent
from packages.trading_agent.agents.market_observer_agent import market_observer_agent
from packages.trading_agent.agents.trade_decision_agent import trade_decision_agent
from packages.trading_agent.agents.trade_execution_agent import trade_execution_agent
from packages.trading_agent.state.trading_state import TradingState
from packages.trading_agent.tools.memory_retrieval import retrieve_similar_memories

logger = get_logger(__name__)


def _sync_db_conn():
    """Return a synchronous psycopg2 connection for persist nodes."""
    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return psycopg2.connect(dsn)


# ── Memory retrieval node ────────────────────────────────────────────────────

def memory_retrieval_node(state: TradingState) -> dict[str, Any]:
    """Fetch similar past market situations from pgvector memory store."""
    observation = state.get("observation")
    symbol = state["symbol"]

    if observation is None:
        return {"retrieved_memories": [], "current_agent": "memory_retrieval"}

    # Build context text for embedding
    context_text = (
        f"{symbol} in {observation.market_regime} regime. "
        f"Price ${observation.current_price:.2f} (24h: {observation.price_change_24h_pct or 0:+.1f}%). "
        f"Technical bias: {observation.technical_bias}. "
        f"RSI: {observation.rsi or 'N/A'}. "
        f"MACD histogram: {observation.macd_histogram or 'N/A'}. "
        f"News sentiment: {observation.news_sentiment} ({observation.sentiment_score:+.2f}). "
        f"Risk level: {observation.risk_level}."
    )

    settings = get_settings()
    memories_json = retrieve_similar_memories.invoke({
        "context_text": context_text,
        "symbol": symbol,
        "limit": settings.memory_retrieval_limit,
        "min_similarity": settings.memory_similarity_threshold,
    })
    memories = json.loads(memories_json)

    return {
        "retrieved_memories": memories,
        "current_agent": "memory_retrieval",
    }


# ── Conditional edge ─────────────────────────────────────────────────────────

def should_execute(state: TradingState) -> str:
    """Route to real execution, virtual simulation, or skip.

    - "execute":         TRADING_ENABLED=true, BUY/SELL, circuit breaker off → Alpaca order
    - "virtual_execute": TRADING_ENABLED=false, BUY/SELL, circuit breaker off → virtual position
    - "skip_execution":  HOLD, or circuit breaker active
    """
    decision = state.get("trade_decision")
    settings = get_settings()

    if not decision or decision.action == "HOLD":
        return "skip_execution"
    if state.get("circuit_breaker_active"):
        return "skip_execution"
    if not settings.trading_enabled:
        return "virtual_execute"
    return "execute"


# ── DB persistence nodes (psycopg2 sync — avoids event loop conflicts) ───────

def _insert_decision_sync(conn, session_id, decision, observation, quantity, memories) -> str:
    """Insert a TradeDecision row and return its UUID string."""
    decision_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO trade_decisions (
                id, session_id, symbol, action, confidence, reasoning,
                signals_json, market_regime, suggested_quantity,
                suggested_entry_price, suggested_stop_loss, suggested_take_profit,
                retrieved_memory_ids, decided_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                decision_id,
                session_id,
                decision.symbol,
                decision.action,
                float(decision.confidence),
                decision.reasoning,
                json.dumps(observation.signals_json if observation else {}),
                decision.market_regime,
                float(quantity) if quantity else None,
                float(observation.current_price) if observation else None,
                float(decision.stop_loss) if decision.stop_loss else None,
                float(decision.take_profit) if decision.take_profit else None,
                json.dumps([m.get("id") for m in (memories or [])]),
                decision.timestamp,
            ),
        )
    return str(decision_id)


def persist_decision_only_node(state: TradingState) -> dict[str, Any]:
    """Persist TradeDecision row when the action is HOLD or execution was skipped."""
    decision = state.get("trade_decision")
    if decision is None:
        return {"current_agent": "persist_decision_only"}

    observation = state.get("observation")
    session_id_str = state.get("session_id", "")
    try:
        session_id = uuid.UUID(session_id_str) if session_id_str else None
    except ValueError:
        session_id = None

    try:
        conn = _sync_db_conn()
        _insert_decision_sync(conn, session_id, decision, observation, None, state.get("retrieved_memories"))
        conn.commit()
        conn.close()
        logger.info("[persist_decision_only] %s: saved %s decision", decision.symbol, decision.action)
    except Exception as e:
        logger.error("[persist_decision_only] Failed for %s: %s", decision.symbol, e)

    return {"current_agent": "persist_decision_only"}


def _close_virtual_long_sync(conn, symbol: str, exit_price: float) -> dict | None:
    """Close the oldest open virtual long for symbol. Returns a summary or None."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, quantity, entry_price FROM trade_positions
            WHERE symbol = %s AND side = 'long' AND status = 'open' AND order_id IS NULL
            ORDER BY opened_at ASC
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        if row is None:
            return None

        entry = float(row["entry_price"])
        qty = float(row["quantity"])
        realized_pnl = (exit_price - entry) * qty
        realized_pnl_pct = (exit_price - entry) / entry * 100 if entry > 0 else 0.0

        cur.execute(
            """
            UPDATE trade_positions
            SET status = 'closed', exit_price = %s, closed_at = %s,
                realized_pnl = %s, realized_pnl_pct = %s,
                exit_reason = 'agent_sell', unrealized_pnl = 0
            WHERE id = %s
            """,
            (
                exit_price,
                datetime.now(timezone.utc),
                round(realized_pnl, 4),
                round(realized_pnl_pct, 4),
                row["id"],
            ),
        )
        return {"position_id": str(row["id"]), "realized_pnl_pct": realized_pnl_pct}


def persist_virtual_position_node(state: TradingState) -> dict[str, Any]:
    """Persist TradeDecision + virtual TradePosition (no Alpaca order) for dry-run BUY/SELL.

    Applies the same deterministic safety gates as trade_execution_agent
    (min confidence, max open positions, no pyramiding) so dry-run behavior
    mirrors live behavior. The virtual portfolio is long-only: SELL closes an
    existing virtual long instead of opening a short.
    """
    decision = state.get("trade_decision")
    observation = state.get("observation")

    if not decision or not observation:
        return {"current_agent": "persist_virtual_position"}

    settings = get_settings()
    session_id_str = state.get("session_id", "")
    try:
        session_id = uuid.UUID(session_id_str) if session_id_str else None
    except ValueError:
        session_id = None

    portfolio = state.get("portfolio_state") or {}
    available_cash = float(portfolio.get("cash") or settings.virtual_starting_capital)
    current_price = observation.current_price

    def _decision_only(reason: str) -> dict[str, Any]:
        logger.info("[virtual] %s: %s — saving decision only", decision.symbol, reason)
        return persist_decision_only_node(state)

    if current_price <= 0:
        return _decision_only("invalid_current_price")

    # Gate: minimum confidence (mirrors execution agent gate 6)
    if decision.confidence < settings.min_decision_confidence:
        return _decision_only(
            f"low_confidence ({decision.confidence:.2f} < {settings.min_decision_confidence:.2f})"
        )

    # ── SELL: close an existing virtual long (long-only portfolio) ───────────
    if decision.action == "SELL":
        try:
            conn = _sync_db_conn()
            _insert_decision_sync(conn, session_id, decision, observation, None, state.get("retrieved_memories"))
            closed = _close_virtual_long_sync(conn, decision.symbol, current_price)
            conn.commit()
            conn.close()
            if closed:
                logger.info(
                    "[virtual] %s: SELL closed virtual long (P&L %+.2f%%)",
                    decision.symbol, closed["realized_pnl_pct"],
                )
            else:
                logger.info("[virtual] %s: SELL with no open virtual long — decision saved only", decision.symbol)
        except Exception as e:
            logger.error("[persist_virtual_position] SELL handling failed for %s: %s", decision.symbol, e)
        return {"current_agent": "persist_virtual_position"}

    # ── BUY: apply position gates, then open a virtual long ──────────────────
    open_symbols = portfolio.get("open_position_symbols") or []
    if decision.symbol in open_symbols:
        return _decision_only(f"symbol_already_open ({decision.symbol})")

    total_open = int(portfolio.get("total_open_positions", 0))
    if total_open >= settings.max_open_positions:
        return _decision_only(f"max_positions_reached ({total_open}/{settings.max_open_positions})")

    raw_capital = decision.position_size_pct * available_cash
    capped_capital = min(raw_capital, settings.max_position_size_usd)
    quantity = round(capped_capital / current_price, 6)

    if quantity <= 0:
        return _decision_only("computed_quantity_zero")

    try:
        conn = _sync_db_conn()
        _insert_decision_sync(conn, session_id, decision, observation, quantity, state.get("retrieved_memories"))
        position_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trade_positions (
                    id, order_id, symbol, side, quantity, entry_price,
                    stop_loss, take_profit, status, opened_at
                ) VALUES (%s, NULL, %s, 'long', %s, %s, %s, %s, 'open', %s)
                """,
                (
                    position_id,
                    decision.symbol,
                    quantity,
                    current_price,
                    float(decision.stop_loss) if decision.stop_loss else None,
                    float(decision.take_profit) if decision.take_profit else None,
                    datetime.now(timezone.utc),
                ),
            )
        conn.commit()
        conn.close()
        logger.info(
            "[virtual] %s: decision saved + virtual position opened qty=%.4f @ $%.2f",
            decision.symbol, quantity, current_price,
        )
    except Exception as e:
        logger.error("[persist_virtual_position] Failed for %s: %s", decision.symbol, e)

    return {"current_agent": "persist_virtual_position"}


def persist_decision_node(state: TradingState) -> dict[str, Any]:
    """Persist TradeDecision + TradeOrder + TradePosition after a real Alpaca execution."""
    decision = state.get("trade_decision")
    execution = state.get("execution_result")
    observation = state.get("observation")

    if not decision or not execution:
        return {"current_agent": "persist_decision"}

    session_id_str = state.get("session_id", "")
    try:
        session_id = uuid.UUID(session_id_str) if session_id_str else None
    except ValueError:
        session_id = None

    try:
        conn = _sync_db_conn()
        decision_id = _insert_decision_sync(
            conn, session_id, decision, observation,
            execution.quantity, state.get("retrieved_memories"),
        )

        order_id = None
        if execution.order_submitted and execution.alpaca_order_id:
            order_id = uuid.uuid4()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_orders (
                        id, decision_id, alpaca_order_id, symbol, side,
                        order_type, quantity, status
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        order_id, uuid.UUID(decision_id),
                        execution.alpaca_order_id, execution.symbol,
                        execution.side or decision.action.lower(),
                        execution.order_type, execution.quantity or 0,
                        execution.status,
                    ),
                )

        if order_id and observation:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_positions (
                        id, order_id, symbol, side, quantity, entry_price,
                        stop_loss, take_profit, status, opened_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'open',%s)
                    """,
                    (
                        uuid.uuid4(), order_id, execution.symbol,
                        "long" if execution.side == "buy" else "short",
                        execution.quantity or 0, observation.current_price,
                        float(decision.stop_loss) if decision.stop_loss else None,
                        float(decision.take_profit) if decision.take_profit else None,
                        datetime.now(timezone.utc),
                    ),
                )

        conn.commit()
        conn.close()
        logger.info(
            "[persist_decision_with_order] %s: saved decision + order alpaca_id=%s",
            decision.symbol, execution.alpaca_order_id,
        )
    except Exception as e:
        logger.error("[persist_decision_node] Failed for %s: %s", decision.symbol, e)

    return {"current_agent": "persist_decision"}


# ── Graph compilation ─────────────────────────────────────────────────────────

def create_trading_graph():
    """Build and compile the 30-minute trading cycle StateGraph.

    Flow:
        START → market_observer → analysis_fetcher (A2A) → memory_retrieval → trade_decision
              → [should_execute conditional]
                  ├── execute        → trade_execution → persist_decision → END
                  ├── virtual_execute → persist_virtual_position → END
                  └── skip_execution  → persist_decision_only → END
    """
    builder = StateGraph(TradingState)

    builder.add_node("market_observer_node", market_observer_agent)
    builder.add_node("analysis_fetcher_node", analysis_fetcher_agent)
    builder.add_node("memory_retrieval_node", memory_retrieval_node)
    builder.add_node("trade_decision_node", trade_decision_agent)
    builder.add_node("trade_execution_node", trade_execution_agent)
    builder.add_node("persist_decision_node", persist_decision_node)
    builder.add_node("persist_decision_only_node", persist_decision_only_node)
    builder.add_node("persist_virtual_position_node", persist_virtual_position_node)

    builder.add_edge(START, "market_observer_node")
    builder.add_edge("market_observer_node", "analysis_fetcher_node")
    builder.add_edge("analysis_fetcher_node", "memory_retrieval_node")
    builder.add_edge("memory_retrieval_node", "trade_decision_node")

    builder.add_conditional_edges(
        "trade_decision_node",
        should_execute,
        {
            "execute": "trade_execution_node",
            "virtual_execute": "persist_virtual_position_node",
            "skip_execution": "persist_decision_only_node",
        },
    )

    builder.add_edge("trade_execution_node", "persist_decision_node")
    builder.add_edge("persist_decision_node", END)
    builder.add_edge("persist_decision_only_node", END)
    builder.add_edge("persist_virtual_position_node", END)

    return builder.compile()


@lru_cache(maxsize=1)
def get_trading_graph():
    """Return the compiled trading cycle graph (singleton)."""
    return create_trading_graph()
