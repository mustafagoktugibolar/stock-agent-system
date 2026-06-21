"""Reflection StateGraph — evaluates past positions and stores memories.

Runs daily at 4:15 PM ET. Processes a list of positions that need reflection
(open positions older than REFLECTION_WINDOW_HOURS, and recently closed
positions without an existing reflection).
"""

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import psycopg2
import psycopg2.extras
from langgraph.graph import END, START, StateGraph

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger
from packages.analysis_agent.tools.market_data import fetch_ohlcv
from packages.trading_agent.agents.reflection_agent import reflection_agent
from packages.trading_agent.state.trading_state import TradingState
from packages.trading_agent.tools.memory_retrieval import store_memory

psycopg2.extras.register_uuid()

logger = get_logger(__name__)


def _sync_db_conn():
    """Return a synchronous psycopg2 connection.

    All DB access in this graph is psycopg2 (sync), matching the trading graph
    persist nodes: graph nodes run in executor threads, where sharing the
    global asyncpg engine across event loops fails.
    """
    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return psycopg2.connect(dsn)


# ── DB query helpers ──────────────────────────────────────────────────────────

def _fetch_positions_needing_reflection(window_hours: int) -> list[dict]:
    """Return positions that are due for reflection but don't have one yet."""
    query = """
        SELECT
            tp.id::text AS id,
            tp.symbol,
            tp.side,
            tp.quantity,
            tp.entry_price,
            tp.exit_price,
            tp.stop_loss,
            tp.take_profit,
            tp.realized_pnl_pct,
            tp.status,
            tp.opened_at,
            tp.closed_at,
            tp.exit_reason,
            tp.order_id::text AS order_id
        FROM trade_positions tp
        LEFT JOIN trade_reflections tr ON tr.position_id = tp.id
        WHERE tr.id IS NULL
          AND (
              (tp.status = 'open' AND tp.opened_at < NOW() - (%s || ' hours')::interval)
              OR
              tp.status IN ('closed', 'stop_hit', 'target_hit')
          )
        ORDER BY tp.opened_at ASC
        LIMIT 20
    """
    conn = _sync_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (str(window_hours),))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _fetch_decision_for_order(order_id_str: str | None) -> dict | None:
    """Fetch the original TradeDecision for a position's order."""
    if not order_id_str:
        return None
    try:
        order_id = uuid.UUID(order_id_str)
    except ValueError:
        return None

    query = """
        SELECT td.id::text AS id, td.action, td.reasoning, td.signals_json,
               td.market_regime, td.confidence
        FROM trade_orders tro
        JOIN trade_decisions td ON td.id = tro.decision_id
        WHERE tro.id = %s
    """
    conn = _sync_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (order_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "id": row["id"],
                "action": row["action"],
                "reasoning": row["reasoning"],
                "signals_json": row["signals_json"] or {},
                "market_regime": row["market_regime"],
                "confidence": float(row["confidence"]),
            }
    finally:
        conn.close()


def _persist_reflection(
    position_id_str: str,
    reflection_data: dict,
    memory_stored: bool,
    exit_price: float | None = None,
) -> str:
    """Persist a TradeReflection row and close virtual positions."""
    try:
        position_id = uuid.UUID(position_id_str)
    except ValueError:
        return ""

    now = datetime.now(timezone.utc)
    reflection_id = uuid.uuid4()

    conn = _sync_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Close virtual positions (order_id IS NULL) after reflection
            cur.execute(
                """
                SELECT side, entry_price FROM trade_positions
                WHERE id = %s AND order_id IS NULL AND status = 'open'
                """,
                (position_id,),
            )
            row = cur.fetchone()
            if row is not None and exit_price:
                entry = float(row["entry_price"])
                if entry > 0:
                    direction = 1.0 if row["side"] == "long" else -1.0
                    realized_pnl_pct = direction * (exit_price - entry) / entry * 100.0
                else:
                    realized_pnl_pct = None
                cur.execute(
                    """
                    UPDATE trade_positions
                    SET status = 'closed', exit_price = %s, closed_at = %s,
                        exit_reason = 'reflection_close', realized_pnl_pct = %s
                    WHERE id = %s
                    """,
                    (exit_price, now, realized_pnl_pct, position_id),
                )

            cur.execute(
                """
                INSERT INTO trade_reflections (
                    id, position_id, symbol, outcome, pnl_pct, what_worked,
                    what_failed, signal_accuracy_json, prediction_vs_reality,
                    lessons_learned, memory_stored, reflected_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    reflection_id,
                    position_id,
                    reflection_data.get("symbol", ""),
                    reflection_data.get("outcome", "inconclusive"),
                    reflection_data.get("pnl_pct"),
                    reflection_data.get("what_worked"),
                    reflection_data.get("what_failed"),
                    json.dumps(reflection_data.get("signal_accuracy", {})),
                    reflection_data.get("prediction_vs_reality"),
                    reflection_data.get("lessons_learned"),
                    memory_stored,
                    now,
                ),
            )
        conn.commit()
        return str(reflection_id)
    finally:
        conn.close()


def _get_current_price(symbol: str) -> float:
    """Fetch the latest close price for a symbol."""
    try:
        ohlcv_json = fetch_ohlcv.invoke({"symbol": symbol, "period": "5d", "interval": "1d"})
        bars = json.loads(ohlcv_json).get("bars", [])
        if bars:
            return float(bars[-1].get("close", 0.0))
    except Exception as e:
        logger.warning("_get_current_price failed for %s: %s", symbol, e)
    return 0.0


# ── Graph nodes ───────────────────────────────────────────────────────────────

def fetch_positions_node(state: TradingState) -> dict[str, Any]:
    """Query DB for positions that need reflection."""
    settings = get_settings()
    positions = _fetch_positions_needing_reflection(settings.reflection_window_hours)
    logger.info("[reflection_graph] Found %d positions to reflect on", len(positions))
    return {"positions_to_reflect": positions, "current_agent": "fetch_positions"}


def load_next_position_node(state: TradingState) -> dict[str, Any]:
    """Pop the next position from the list and load its decision context."""
    positions = list(state.get("positions_to_reflect") or [])
    if not positions:
        return {
            "current_position_for_reflection": None,
            "original_decision_for_reflection": None,
            "positions_to_reflect": [],
            "current_agent": "load_position",
        }

    position = positions.pop(0)
    symbol = position.get("symbol", "UNKNOWN")
    order_id = position.get("order_id")

    decision = _fetch_decision_for_order(order_id)

    # Get current/exit price for PnL computation
    exit_price = position.get("exit_price")
    if exit_price:
        current_price = float(exit_price)
    else:
        current_price = _get_current_price(symbol)

    position["current_price_for_reflection"] = current_price

    logger.info(
        "[reflection_graph] Processing %s position_id=%s current_price=%.4f",
        symbol, position.get("id"), current_price,
    )

    return {
        "positions_to_reflect": positions,
        "current_position_for_reflection": position,
        "original_decision_for_reflection": decision,
        "current_agent": "load_position",
    }


def store_memory_node(state: TradingState) -> dict[str, Any]:
    """Store the reflection as a retrievable memory if warranted."""
    reflection = state.get("reflection")
    position = state.get("current_position_for_reflection") or {}
    decision = state.get("original_decision_for_reflection") or {}

    if not reflection or not reflection.should_store_memory:
        return {"current_agent": "store_memory"}

    symbol = reflection.symbol
    entry_price = float(position.get("entry_price", 0))
    situation_text = (
        f"{symbol} in {decision.get('market_regime', 'unknown')} regime. "
        f"Entry at ${entry_price:.4f}. "
        f"Technical and sentiment signals led to a {decision.get('action', 'BUY')} decision "
        f"with confidence {decision.get('confidence', 0.0):.2f}."
    )
    decision_text = decision.get("reasoning", "")[:500]
    outcome_text = (
        f"Position {reflection.outcome}. PnL: {reflection.pnl_pct:+.2f}%."
        if reflection.pnl_pct is not None
        else f"Position {reflection.outcome}."
    )

    result_json = store_memory.invoke({
        "symbol": symbol,
        "market_regime": decision.get("market_regime", "ranging"),
        "outcome_label": reflection.outcome if reflection.outcome in ("profitable", "loss", "breakeven") else "breakeven",
        "situation_text": situation_text,
        "decision_text": decision_text,
        "outcome_text": outcome_text,
        "lessons_text": reflection.lessons_learned,
        "pnl_pct": reflection.pnl_pct,
        "confidence_at_decision": decision.get("confidence"),
        "reflection_id": None,
    })
    result = json.loads(result_json)
    logger.info("[reflection_graph] Memory stored: %s", result.get("memory_id"))
    return {"current_agent": "store_memory"}


def persist_reflection_node(state: TradingState) -> dict[str, Any]:
    """Save the TradeReflection row to DB."""
    reflection = state.get("reflection")
    position = state.get("current_position_for_reflection")

    if not reflection or not position:
        return {"current_agent": "persist_reflection"}

    reflection_dict = reflection.model_dump()
    memory_stored = reflection.should_store_memory

    exit_price = position.get("current_price_for_reflection") or position.get("exit_price")
    _persist_reflection(
        position_id_str=str(position.get("id", "")),
        reflection_data=reflection_dict,
        memory_stored=memory_stored,
        exit_price=float(exit_price) if exit_price else None,
    )

    logger.info(
        "[reflection_graph] %s: reflection persisted (outcome=%s memory_stored=%s)",
        reflection.symbol, reflection.outcome, memory_stored,
    )
    return {
        "reflection": None,
        "current_position_for_reflection": None,
        "original_decision_for_reflection": None,
        "current_agent": "persist_reflection",
    }


# ── Conditional edges ─────────────────────────────────────────────────────────

def has_more_positions(state: TradingState) -> str:
    """Check if there are more positions left to process."""
    if state.get("positions_to_reflect"):
        return "continue"
    return "done"


def should_store_memory_edge(state: TradingState) -> str:
    reflection = state.get("reflection")
    if reflection and reflection.should_store_memory:
        return "store"
    return "skip_store"


# ── Graph compilation ─────────────────────────────────────────────────────────

def create_reflection_graph():
    """Build and compile the daily reflection StateGraph.

    Flow:
        START → fetch_positions → load_next_position → reflection_agent
              → [should_store_memory]
                  ├── store → store_memory_node → persist_reflection → [has_more]
                  └── skip  → persist_reflection → [has_more]
                                  ├── continue → load_next_position (loop)
                                  └── done → END
    """
    builder = StateGraph(TradingState)

    builder.add_node("fetch_positions_node", fetch_positions_node)
    builder.add_node("load_next_position_node", load_next_position_node)
    builder.add_node("reflection_agent_node", reflection_agent)
    builder.add_node("store_memory_node", store_memory_node)
    builder.add_node("persist_reflection_node", persist_reflection_node)

    builder.add_edge(START, "fetch_positions_node")
    builder.add_edge("fetch_positions_node", "load_next_position_node")
    builder.add_edge("load_next_position_node", "reflection_agent_node")

    builder.add_conditional_edges(
        "reflection_agent_node",
        should_store_memory_edge,
        {
            "store": "store_memory_node",
            "skip_store": "persist_reflection_node",
        },
    )

    builder.add_edge("store_memory_node", "persist_reflection_node")

    builder.add_conditional_edges(
        "persist_reflection_node",
        has_more_positions,
        {
            "continue": "load_next_position_node",
            "done": END,
        },
    )

    return builder.compile()


@lru_cache(maxsize=1)
def get_reflection_graph():
    """Return the compiled reflection graph (singleton)."""
    return create_reflection_graph()
