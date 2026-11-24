from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaymentTransaction(Base):
    """One Safepay Raast QR payment and its single authorized door-unlock attempt."""

    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint("tracker_token", name="uq_payment_transactions_tracker_token"),
        Index("ix_payment_transactions_station_created", "station_id", "created_at"),
        Index("ix_payment_transactions_device_status", "device_id", "payment_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True)
    door_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="SAFEPAY")
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False, default="RAAST_DYNAMIC_QR")
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    tracker_token: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")

    payment_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    provider_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tracker_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unlock_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")

    qr_payload: Mapped[str] = mapped_column(Text, nullable=False)
    qr_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unlock_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_event_id: Mapped[int | None] = mapped_column(ForeignKey("access_events.id", ondelete="SET NULL"), nullable=True)

    provider_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
