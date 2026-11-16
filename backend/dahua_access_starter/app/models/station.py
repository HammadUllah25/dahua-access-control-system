from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Station(Base):
    """A petrol station/site that owns one or more access controllers."""

    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    station_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    devices = relationship("Device", back_populates="station")
    card_assignments = relationship("StationCardAssignment", back_populates="station")
    rates = relationship("StationRate", back_populates="station", cascade="all, delete-orphan")
    cash_collections = relationship("CashCollection", back_populates="station")
