from __future__ import annotations

from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AccessCard(Base):
    """A person's IC card assignment to one physical controller."""

    __tablename__ = "access_cards"
    __table_args__ = (UniqueConstraint("device_id", "card_number", name="uq_device_card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    card_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    card_name: Mapped[str] = mapped_column(String(64), nullable=False)
    device_record_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_type: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Preserve the raw native Dahua card state (normal/lost/logoff/frozen/etc.).
    device_card_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    door_indices: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    time_section_indices: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    last_sync_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    person = relationship("Person", back_populates="cards")
    device = relationship("Device", back_populates="cards")
