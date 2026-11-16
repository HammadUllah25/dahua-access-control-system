from __future__ import annotations

from datetime import date, datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StationCardAssignment(Base):
    """A station-scoped physical card record mirrored to a Dahua controller.

    The legacy USER/STAFF fields remain for compatibility with earlier API
    versions. New named station-user ownership and operational roles are
    maintained in UserCardAssignment and StationUser, not in this row.
    """

    __tablename__ = "station_card_assignments"
    __table_args__ = (
        UniqueConstraint("device_id", "card_number", name="uq_station_device_card_number"),
        CheckConstraint("role IN ('USER', 'STAFF')", name="ck_station_card_role"),
        Index("ix_station_cards_station_role", "station_id", "role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    card_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    card_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER", server_default="USER")
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    device_record_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_type: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    device_card_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    door_indices: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    time_section_indices: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    sync_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    last_sync_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    station = relationship("Station", back_populates="card_assignments")
    device = relationship("Device", back_populates="station_card_assignments")
