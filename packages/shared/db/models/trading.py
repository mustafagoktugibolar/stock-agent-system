"""ORM models for the self-improving paper trading module.

Six tables:
  trading_sessions    — one active session per day, tracks capital and config
  trade_decisions     — every observe→reason output (BUY/SELL/HOLD)
  trade_orders        — Alpaca order records linked to decisions
  trade_positions     — open and closed position lifecycle
  trade_reflections   — post-trade self-critique linked to positions
  agent_memories      — retrievable pgvector memories built from reflections
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db.base import Base


class TradingSession(Base):
    __tablename__ = "trading_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    strategy_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    watchlist: Mapped[dict] = mapped_column(JSON, nullable=False)
    config_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_trading_sessions_status", "status"),
    )


class TradeDecision(Base):
    __tablename__ = "trade_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    signals_json: Mapped[Optional[dict]] = mapped_column(JSON)
    market_regime: Mapped[Optional[str]] = mapped_column(String(30))
    suggested_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    suggested_entry_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    suggested_stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    suggested_take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    retrieved_memory_ids: Mapped[Optional[dict]] = mapped_column(JSON)
    decided_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_trade_decisions_symbol_decided_at", "symbol", "decided_at"),
    )


class TradeOrder(Base):
    __tablename__ = "trade_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alpaca_order_id: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(5), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    limit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    filled_avg_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    filled_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 6))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    alpaca_submitted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    alpaca_filled_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    raw_alpaca_response: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_trade_orders_decision_id"),
        UniqueConstraint("alpaca_order_id", name="uq_trade_orders_alpaca_id"),
        Index("idx_trade_orders_status", "status"),
    )


class TradePosition(Base):
    __tablename__ = "trade_positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_orders.id", ondelete="SET NULL"),
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(5), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    realized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    realized_pnl_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    unrealized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_trade_positions_symbol_status", "symbol", "status"),
    )


class TradeReflection(Base):
    __tablename__ = "trade_reflections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    pnl_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    what_worked: Mapped[Optional[str]] = mapped_column(Text)
    what_failed: Mapped[Optional[str]] = mapped_column(Text)
    signal_accuracy_json: Mapped[Optional[dict]] = mapped_column(JSON)
    prediction_vs_reality: Mapped[Optional[str]] = mapped_column(Text)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text)
    memory_stored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reflected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("position_id", name="uq_trade_reflections_position_id"),
        Index("idx_trade_reflections_outcome", "outcome"),
    )


class AgentMemory(Base):
    """Retrievable memory built from trade reflections.

    The `embedding` column uses pgvector's Vector(1536) type (OpenAI
    text-embedding-3-small). CREATE EXTENSION vector must run before this table
    is created — handled in session.py's create_tables(). The HNSW index is
    created via raw SQL after create_all() because SQLAlchemy DDL does not
    support custom index access methods.
    """

    __tablename__ = "agent_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reflection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_reflections.id", ondelete="SET NULL"),
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    market_regime: Mapped[str] = mapped_column(String(30), nullable=False)
    outcome_label: Mapped[str] = mapped_column(String(20), nullable=False)
    situation_text: Mapped[str] = mapped_column(Text, nullable=False)
    decision_text: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_text: Mapped[str] = mapped_column(Text, nullable=False)
    lessons_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))
    confidence_at_decision: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    pnl_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_agent_memories_symbol_regime", "symbol", "market_regime"),
    )
