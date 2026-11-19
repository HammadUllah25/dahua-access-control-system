from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.access_event import AccessEvent
from app.schemas.access_event import AccessEventRead

router = APIRouter(prefix="/access-events", tags=["Access Events"])
PKT = ZoneInfo("Asia/Karachi")


@router.get("", response_model=list[AccessEventRead])
def list_access_events(
    device_id: int | None = Query(default=None, gt=0),
    card_number: str | None = Query(default=None, max_length=32),
    station_id: int | None = Query(default=None, gt=0),
    card_role: str | None = Query(default=None, max_length=20, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,19}$"),
    event_source: str | None = Query(default=None, max_length=20),
    event_type: str | None = Query(default=None, max_length=40),
    user_type: str | None = Query(default=None, max_length=20),
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List newest-first access events for dashboards, with optional device/card filters."""
    query = db.query(AccessEvent)
    if device_id is not None:
        query = query.filter(AccessEvent.device_id == device_id)
    if card_number:
        query = query.filter(AccessEvent.card_number == card_number.strip().upper())
    if station_id is not None:
        query = query.filter(AccessEvent.station_id == station_id)
    if card_role:
        query = query.filter(AccessEvent.card_role == card_role.strip().upper())
    if event_source:
        query = query.filter(AccessEvent.event_source == event_source.strip().upper())
    if event_type:
        query = query.filter(AccessEvent.event_type == event_type.strip().upper())
    if user_type:
        query = query.filter(AccessEvent.user_type == user_type.strip().upper())
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if start_date:
        start_utc = datetime.combine(start_date, time.min, tzinfo=PKT).astimezone(timezone.utc)
        query = query.filter(AccessEvent.received_at >= start_utc)
    if end_date:
        end_utc = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=PKT).astimezone(timezone.utc)
        query = query.filter(AccessEvent.received_at < end_utc)
    return query.order_by(AccessEvent.received_at.desc(), AccessEvent.id.desc()).offset(offset).limit(limit).all()


@router.get("/summary")
def access_event_summary(
    device_id: int | None = Query(default=None, gt=0),
    station_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    """Return aggregate counters for access-event dashboard cards."""
    query = db.query(AccessEvent)
    if device_id is not None:
        query = query.filter(AccessEvent.device_id == device_id)
    if station_id is not None:
        query = query.filter(AccessEvent.station_id == station_id)
    total = query.with_entities(func.count(AccessEvent.id)).scalar() or 0
    granted = query.filter(AccessEvent.access_result == "granted").with_entities(
        func.count(AccessEvent.id)
    ).scalar() or 0
    denied = query.filter(AccessEvent.access_result == "denied").with_entities(
        func.count(AccessEvent.id)
    ).scalar() or 0
    unknown = max(total - granted - denied, 0)
    return {"total": total, "granted": granted, "denied": denied, "unknown": unknown}


@router.get("/{event_id}", response_model=AccessEventRead)
def get_access_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(AccessEvent, event_id)
    if event is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Access event not found")
    return event
