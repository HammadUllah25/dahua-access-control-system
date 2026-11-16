from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StationUser(Base):
    """A named person/label at a station; this is not a dashboard login."""

    __tablename__ = "station_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("operational_roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    # None means inherit OperationalRole.default_is_billable.
    is_billable_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    station = relationship("Station")
    operational_role = relationship("OperationalRole", back_populates="users")
    card_assignments = relationship("UserCardAssignment", back_populates="station_user")
