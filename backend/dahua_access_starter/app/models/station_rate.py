from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StationRate(Base):
    """Effective-dated per-entry rate. Events snapshot the rate at scan time."""

    __tablename__ = "station_rates"
    __table_args__ = (
        CheckConstraint("role IN ('USER', 'STAFF')", name="ck_station_rate_role"),
        CheckConstraint("rate_per_use >= 0", name="ck_station_rate_nonnegative"),
        Index("ix_station_rate_effective", "station_id", "role", "effective_from", "effective_until"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    rate_per_use: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR", server_default="PKR")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    station = relationship("Station", back_populates="rates")
