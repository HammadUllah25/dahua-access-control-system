from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    station_id: Mapped[int | None] = mapped_column(ForeignKey("stations.id", ondelete="SET NULL"), nullable=True, index=True)
    connection_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ip_domain")
    host: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=37777)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True, default="ASI1201E")
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_tcp_reachable_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_connect_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    inventory_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", server_default="unknown")
    last_inventory_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_card_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_card_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    station = relationship("Station", back_populates="devices")
    station_card_assignments = relationship("StationCardAssignment", back_populates="device", cascade="all, delete-orphan")
    cards = relationship("AccessCard", back_populates="device", cascade="all, delete-orphan")
    access_events = relationship("AccessEvent", back_populates="device")
