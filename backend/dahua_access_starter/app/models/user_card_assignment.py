from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserCardAssignment(Base):
    """Historical link between one station user and one station card record.

    The underlying StationCardAssignment remains the controller credential.
    This table records who owns it now and who owned it previously.
    """

    __tablename__ = "user_card_assignments"
    __table_args__ = (
        Index(
            "ux_user_card_assignment_active_user", "station_user_id", unique=True,
            sqlite_where=text("is_active = 1"), postgresql_where=text("is_active = true"),
        ),
        Index(
            "ux_user_card_assignment_active_card", "station_card_assignment_id", unique=True,
            sqlite_where=text("is_active = 1"), postgresql_where=text("is_active = true"),
        ),
        Index(
            "ux_user_card_assignment_active_uid", "card_number", unique=True,
            sqlite_where=text("is_active = 1"), postgresql_where=text("is_active = true"),
        ),
        Index("ix_user_card_assignment_station_active", "station_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    station_user_id: Mapped[int] = mapped_column(ForeignKey("station_users.id", ondelete="RESTRICT"), nullable=False, index=True)
    station_card_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("station_card_assignments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True)
    card_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    station_user = relationship("StationUser", back_populates="card_assignments")
    station_card_assignment = relationship("StationCardAssignment")
