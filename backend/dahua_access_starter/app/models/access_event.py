from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AccessEvent(Base):
    """Immutable access-control event received from a Dahua controller."""

    __tablename__ = "access_events"
    __table_args__ = (
        Index("ix_access_events_device_received", "device_id", "received_at"),
        Index("ix_access_events_card_received", "card_number", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Nullable to preserve the audit record if a device is later deleted.
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    device_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)

    alarm_type: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    door_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    door_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    card_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cardholder_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reader_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_direction: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    event_type_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_method: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_type: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Keep unclassified raw result values until they are validated against real device scans.
    access_result: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown", server_default="unknown")
    raw_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_em_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # stuTime is device-local. RealUTC is stored separately only when the SDK marks it valid.
    device_event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    event_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    device = relationship("Device", back_populates="access_events")
