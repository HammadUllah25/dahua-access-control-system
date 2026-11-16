from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeviceSyncJob(Base):
    """Audit trail for inventory checks and controlled cloud-to-device restoration."""

    __tablename__ = "device_sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    station_id: Mapped[int | None] = mapped_column(ForeignKey("stations.id", ondelete="SET NULL"), nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    expected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    observed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_cards: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    unexpected_cards: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device = relationship("Device")
