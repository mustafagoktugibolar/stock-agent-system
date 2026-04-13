import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import ARRAY, JSON, TIMESTAMP, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db.base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False, default="1d")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    recommendation: Mapped[Optional[str]] = mapped_column(String(10))
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    time_horizon: Mapped[Optional[str]] = mapped_column(String(20))
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    technical_json: Mapped[Optional[dict]] = mapped_column(JSON)
    news_json: Mapped[Optional[dict]] = mapped_column(JSON)
    risk_json: Mapped[Optional[dict]] = mapped_column(JSON)
    full_state_json: Mapped[Optional[dict]] = mapped_column(JSON)
    errors: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
