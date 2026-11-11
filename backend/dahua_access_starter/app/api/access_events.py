from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.access_event import AccessEvent
from app.schemas.access_event import AccessEventRead

router = APIRouter(prefix="/access-events", tags=["Access Events"])


@router.get("", response_model=list[AccessEventRead])
def list_access_events(
    device_id: int | None = Query(default=None, gt=0),
    card_number: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List newest-first access events for dashboards, with optional device/card filters."""
    query = db.query(AccessEvent)
    if device_id is not None:
        query = query.filter(AccessEvent.device_id == device_id)
    if card_number:
        query = query.filter(AccessEvent.card_number == card_number.strip())
    return query.order_by(AccessEvent.received_at.desc(), AccessEvent.id.desc()).offset(offset).limit(limit).all()


@router.get("/summary")
def access_event_summary(
    device_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    """Return aggregate counters for access-event dashboard cards."""
    query = db.query(AccessEvent)
    if device_id is not None:
        query = query.filter(AccessEvent.device_id == device_id)
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
