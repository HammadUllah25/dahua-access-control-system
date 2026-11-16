from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CashCollection(Base):
    """A recorded cash remittance for a station and reporting period."""

    __tablename__ = "cash_collections"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_cash_collection_nonnegative"),
        CheckConstraint("period_end >= period_start", name="ck_cash_collection_period"),
        Index("ix_cash_collections_station_received", "station_id", "collected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR", server_default="PKR")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    received_by: Mapped[str] = mapped_column(String(120), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    station = relationship("Station", back_populates="cash_collections")
