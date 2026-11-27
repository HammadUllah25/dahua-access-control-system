from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.station import Station
from app.models.device import Device
from app.models.station_card_assignment import StationCardAssignment
from app.models.user_card_assignment import UserCardAssignment
from app.models.station_user import StationUser
from app.models.operational_role import OperationalRole
from app.models.station_rate import StationRate
from app.models.cash_collection import CashCollection
from app.models.device_sync_job import DeviceSyncJob
from app.models.access_event import AccessEvent
from app.models.access_card import AccessCard
from app.schemas.device import DeviceRead
from app.schemas.stations import (
    StationCreate, StationUpdate, StationRead,
    StationCardCreate, StationCardAdoptRequest, StationCardUpdate, StationCardRead,
    StationRateCreate, StationRateRead,
    CashCollectionCreate, CashCollectionRead,
    ReprovisionRequest, ManualReprovisionVerificationRequest, InventoryCheckRead,
    DatabaseOnlyStationCardDeleteRequest,
)
from app.services.access_cards import access_cards, AccessCardSDKError
from app.services.device_sessions import sessions
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError
from app.services.secret_store import decrypt_secret

router = APIRouter(tags=["Stations, Cards and Finance"])
PKT = ZoneInfo("Asia/Karachi")
UTC = timezone.utc


def _station_or_404(db: Session, station_id: int) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


def _device_or_404(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _assignment_or_404(db: Session, station_id: int, assignment_id: int) -> StationCardAssignment:
    assignment = db.query(StationCardAssignment).filter(
        StationCardAssignment.id == assignment_id,
        StationCardAssignment.station_id == station_id,
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Station card assignment not found")
    return assignment


def _ensure_connected(device: Device, db: Session) -> None:
    if sessions.is_connected(device.id):
        return
    try:
        session = sessions.connect(device)
        device.status = "online"
        device.serial_number = session.serial_number or device.serial_number
        device.last_connected_at = session.connected_at
        device.last_error = None
        db.commit()
    except (SDKUnavailableError, DeviceLoginError, ValueError) as exc:
        device.status = "offline"
        device.last_error = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail=f"Could not connect to Dahua device: {exc}") from exc


def _card_type_value(value: str) -> int:
    return {"general": 0, "vip": 1, "guest": 2}[value]


def _local_report_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(start_date, time.min, tzinfo=PKT)
    end_local = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=PKT)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _event_date_local(event: AccessEvent) -> date:
    return _as_utc(event.received_at).astimezone(PKT).date()


def _money(value: Decimal | None) -> Decimal:
    return Decimal("0.00") if value is None else Decimal(value).quantize(Decimal("0.01"))


def _report_query(
    db: Session,
    *,
    station_id: int | None,
    start_date: date,
    end_date: date,
):
    start_utc, end_utc = _local_report_bounds(start_date, end_date)
    query = db.query(AccessEvent).filter(
        AccessEvent.received_at >= start_utc,
        AccessEvent.received_at < end_utc,
    )
    if station_id is not None:
        query = query.filter(AccessEvent.station_id == station_id)
    return query.order_by(AccessEvent.received_at.asc(), AccessEvent.id.asc())


def _summary_for_range(db: Session, station_id: int | None, start_date: date, end_date: date) -> dict:
    events = _report_query(
        db, station_id=station_id, start_date=start_date, end_date=end_date
    ).all()
    user_entries = sum(
        1 for event in events
        if event.access_result == "granted" and event.event_direction.upper() == "ENTRY"
        and event.card_role in {"USER", "CUSTOMER"}
    )
    staff_entries = sum(
        1 for event in events
        if event.access_result == "granted" and event.event_direction.upper() == "ENTRY" and event.card_role == "STAFF"
    )
    billable_events = [event for event in events if event.is_billable]
    expected = sum((_money(event.rate_applied) for event in billable_events), Decimal("0.00"))
    unpriced = sum(1 for event in billable_events if event.rate_applied is None)
    start_utc, end_utc = _local_report_bounds(start_date, end_date)
    # Collection records are allocated to the usage period they settle. Keep
    # this separate from the date cash was physically received so the reports
    # do not compare one month's usage to an unrelated payment date.
    period_collections_query = db.query(CashCollection).filter(
        CashCollection.period_start >= start_date,
        CashCollection.period_end <= end_date,
    )
    receipt_collections_query = db.query(CashCollection).filter(
        CashCollection.collected_at >= start_utc,
        CashCollection.collected_at < end_utc,
    )
    if station_id is not None:
        period_collections_query = period_collections_query.filter(CashCollection.station_id == station_id)
        receipt_collections_query = receipt_collections_query.filter(CashCollection.station_id == station_id)
    period_collections = period_collections_query.all()
    receipt_collections = receipt_collections_query.all()
    collected = sum((_money(item.amount) for item in period_collections), Decimal("0.00"))
    cash_received = sum((_money(item.amount) for item in receipt_collections), Decimal("0.00"))
    granted = sum(1 for event in events if event.access_result == "granted")
    denied = sum(1 for event in events if event.access_result == "denied")
    return {
        "station_id": station_id,
        "start_date": start_date,
        "end_date": end_date,
        "total_scans": len(events),
        "granted_scans": granted,
        "denied_scans": denied,
        "user_entries": user_entries,
        "staff_entries": staff_entries,
        "manager_entries": sum(1 for event in events if event.access_result == "granted" and event.event_direction.upper() == "ENTRY" and event.card_role == "MANAGER"),
        "admin_entries": sum(1 for event in events if event.access_result == "granted" and event.event_direction.upper() == "ENTRY" and event.card_role == "ADMIN"),
        "billable_entries": len(billable_events),
        "unpriced_billable_entries": unpriced,
        "expected_collection": expected,
        "actual_cash_collected": collected,
        "cash_received_during_report_period": cash_received,
        "outstanding_balance": (expected - collected).quantize(Decimal("0.01")),
        "currency": "PKR",
        "note": "Expected collection uses the rate snapshot stored with each billable event. Actual cash collected is allocated by each collection's usage period; cash_received_during_report_period is based on the physical receipt timestamp.",
    }


# --------------------------- Station management ---------------------------

@router.post("/stations", response_model=StationRead, status_code=status.HTTP_201_CREATED)
def create_station(payload: StationCreate, db: Session = Depends(get_db)):
    code = payload.station_code.strip().upper()
    if db.query(Station).filter(Station.station_code == code).first():
        raise HTTPException(status_code=409, detail="station_code already exists")
    station = Station(
        station_code=code,
        name=payload.name.strip(),
        address=payload.address.strip() if payload.address else None,
        city=payload.city.strip() if payload.city else None,
        contact_name=payload.contact_name.strip() if payload.contact_name else None,
        contact_phone=payload.contact_phone.strip() if payload.contact_phone else None,
        is_active=payload.is_active,
    )
    db.add(station)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="station_code already exists") from exc
    db.refresh(station)
    return station


@router.get("/stations", response_model=list[StationRead])
def list_stations(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Station)
    if active_only:
        query = query.filter(Station.is_active.is_(True))
    return query.order_by(Station.station_code.asc()).all()


@router.get("/stations/{station_id}", response_model=StationRead)
def get_station(station_id: int, db: Session = Depends(get_db)):
    return _station_or_404(db, station_id)


@router.put("/stations/{station_id}", response_model=StationRead)
def update_station(station_id: int, payload: StationUpdate, db: Session = Depends(get_db)):
    station = _station_or_404(db, station_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("station_code"):
        values["station_code"] = values["station_code"].strip().upper()
        duplicate = db.query(Station).filter(
            Station.station_code == values["station_code"], Station.id != station_id
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="station_code already exists")
    for key, value in values.items():
        setattr(station, key, value.strip() if isinstance(value, str) else value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Station update conflicts with an existing station") from exc
    db.refresh(station)
    return station


@router.post("/stations/{station_id}/devices/{device_id}", response_model=DeviceRead)
def assign_device_to_station(station_id: int, device_id: int, db: Session = Depends(get_db)):
    station = _station_or_404(db, station_id)
    device = _device_or_404(db, device_id)
    if device.station_id is not None and device.station_id != station_id:
        raise HTTPException(status_code=409, detail="Device is already assigned to another station")
    device.station_id = station.id
    db.commit()
    db.refresh(device)
    return device


@router.delete("/stations/{station_id}/devices/{device_id}")
def unassign_device_from_station(station_id: int, device_id: int, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    device = _device_or_404(db, device_id)
    if device.station_id != station_id:
        raise HTTPException(status_code=404, detail="Device is not assigned to this station")
    assignments = db.query(StationCardAssignment).filter(
        StationCardAssignment.station_id == station_id,
        StationCardAssignment.device_id == device_id,
    ).count()
    if assignments:
        raise HTTPException(status_code=409, detail="Move or deactivate the station card assignments before unassigning this device")
    device.station_id = None
    db.commit()
    return {"unassigned": True, "station_id": station_id, "device_id": device_id}


@router.get("/stations/{station_id}/devices", response_model=list[DeviceRead])
def list_station_devices(station_id: int, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    return db.query(Device).filter(Device.station_id == station_id).order_by(Device.id.asc()).all()


# ------------------------------- Card roles -------------------------------

@router.post("/stations/{station_id}/cards", response_model=StationCardRead, status_code=status.HTTP_201_CREATED)
def create_station_card(station_id: int, payload: StationCardCreate, db: Session = Depends(get_db)):
    station = _station_or_404(db, station_id)
    if not station.is_active:
        raise HTTPException(status_code=409, detail="Cannot add cards to an inactive station")
    device = _device_or_404(db, payload.device_id)
    if device.station_id != station_id:
        raise HTTPException(status_code=409, detail="Assign this Dahua device to the station before adding station cards")
    card_number = payload.card_number.upper()
    duplicate_station_card = db.query(StationCardAssignment).filter(
        StationCardAssignment.device_id == device.id,
        StationCardAssignment.card_number == card_number,
    ).first()
    duplicate_legacy_card = db.query(AccessCard).filter(
        AccessCard.device_id == device.id,
        AccessCard.card_number == card_number,
    ).first()
    if duplicate_station_card or duplicate_legacy_card:
        raise HTTPException(status_code=409, detail="This RFID card is already registered to this controller")

    _ensure_connected(device, db)
    card_name = (payload.card_name or f"{payload.role} {card_number[-8:]}").strip()
    is_billable = payload.is_billable if payload.is_billable is not None else payload.role == "USER"
    try:
        record_number = access_cards.add_device_card(
            device.id,
            card_number=card_number,
            card_name=card_name,
            card_type=_card_type_value(payload.card_type),
            is_valid=payload.is_valid,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            door_indices=payload.door_indices,
            time_section_indices=payload.time_section_indices,
        )
    except AccessCardSDKError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    assignment = StationCardAssignment(
        station_id=station_id,
        device_id=device.id,
        card_number=card_number,
        card_name=card_name,
        role=payload.role,
        is_billable=is_billable,
        is_active=True,
        device_record_no=record_number,
        card_type=_card_type_value(payload.card_type),
        device_card_status=0 if payload.is_valid else 4,
        is_valid=payload.is_valid,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        door_indices=payload.door_indices,
        time_section_indices=payload.time_section_indices,
        sync_status="pending_verification",
        last_synced_at=datetime.now(UTC),
    )
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        try:
            access_cards.delete_device_card(device.id, record_number)
        except AccessCardSDKError:
            pass
        raise HTTPException(
            status_code=409,
            detail="Controller accepted the card but the application could not save it. A controller cleanup was attempted; verify device records.",
        ) from exc
    db.refresh(assignment)
    return assignment


@router.post(
    "/stations/{station_id}/cards/adopt-existing",
    response_model=StationCardRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Stations, Cards and Finance"],
    summary="Adopt an existing person-based card into a station role",
    description=(
        "Copies an existing cloud AccessCard assignment into the station-based USER/STAFF model. "
        "It does not enroll, modify, or delete anything on the physical controller and does not "
        "delete the legacy person/card records. Use this after reviewing the role, then run the "
        "confirmed factory-reset reprovision action to restore cards to a controller known to be empty."
    ),
)
def adopt_existing_person_card(
    station_id: int,
    payload: StationCardAdoptRequest,
    db: Session = Depends(get_db),
):
    station = _station_or_404(db, station_id)
    if not station.is_active:
        raise HTTPException(status_code=409, detail="Cannot add cards to an inactive station")

    device = _device_or_404(db, payload.device_id)
    if device.station_id != station_id:
        raise HTTPException(status_code=409, detail="Assign this Dahua device to the station before adopting cards")

    card_number = payload.card_number.upper()
    legacy_card = db.query(AccessCard).filter(
        AccessCard.device_id == device.id,
        AccessCard.card_number == card_number,
    ).first()
    if legacy_card is None:
        raise HTTPException(
            status_code=404,
            detail="No existing person-based card assignment was found for this card and controller",
        )

    existing_station_card = db.query(StationCardAssignment).filter(
        StationCardAssignment.device_id == device.id,
        StationCardAssignment.card_number == card_number,
    ).first()
    if existing_station_card is not None:
        raise HTTPException(
            status_code=409,
            detail=f"This card already has station assignment ID {existing_station_card.id}",
        )

    # Do not copy device_record_no: a factory reset invalidates the old native
    # record number. The reprovision endpoint will save the new one returned by
    # the controller after it accepts the card insert.
    assignment = StationCardAssignment(
        station_id=station_id,
        device_id=device.id,
        card_number=card_number,
        card_name=(payload.card_name or legacy_card.card_name or f"{payload.role} {card_number[-8:]}").strip(),
        role=payload.role,
        is_billable=(payload.is_billable if payload.is_billable is not None else payload.role == "USER"),
        is_active=True,
        device_record_no=None,
        card_type=legacy_card.card_type,
        device_card_status=0 if legacy_card.is_valid else 4,
        is_valid=legacy_card.is_valid,
        valid_from=legacy_card.valid_from or date.today(),
        valid_until=legacy_card.valid_until or date(2037, 12, 31),
        door_indices=legacy_card.door_indices or [0],
        time_section_indices=legacy_card.time_section_indices or [0],
        sync_status="needs_reprovisioning",
        last_sync_error="Adopted from the existing person-based record; restore to the controller before use.",
        last_synced_at=None,
    )
    db.add(assignment)
    try:
        db.flush()
        device.inventory_status = "needs_reprovisioning"
        device.expected_card_count = db.query(StationCardAssignment).filter(
            StationCardAssignment.device_id == device.id
        ).count()
        # Leave observed_card_count unknown. A visible empty list in SmartPSS is
        # a human check, not a successful SDK inventory read.
        device.observed_card_count = None
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This card already has a station assignment") from exc

    db.refresh(assignment)
    return assignment




@router.post("/stations/{station_id}/cards/database-only-delete", tags=["Administrative Maintenance"])
def delete_station_cards_database_only(
    station_id: int,
    payload: DatabaseOnlyStationCardDeleteRequest,
    db: Session = Depends(get_db),
):
    """Remove orphaned cloud station-card rows without contacting the controller.

    This is a guarded cleanup tool, not part of normal user/card management.
    Rows with any user-card history are protected so audit ownership is kept.
    """
    _station_or_404(db, station_id)
    assignments = db.query(StationCardAssignment).filter(
        StationCardAssignment.station_id == station_id,
        StationCardAssignment.id.in_(payload.assignment_ids),
    ).order_by(StationCardAssignment.id.asc()).all()
    if len(assignments) != len(payload.assignment_ids):
        raise HTTPException(status_code=404, detail="One or more station card assignments were not found for this station")

    assignment_ids = [item.id for item in assignments]
    history_rows = db.query(UserCardAssignment.station_card_assignment_id).filter(
        UserCardAssignment.station_card_assignment_id.in_(assignment_ids)
    ).all()
    protected_ids = sorted({int(row[0]) for row in history_rows})
    if protected_ids:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Some card assignments have user-card history and cannot be hard-deleted.",
                "protected_assignment_ids": protected_ids,
                "note": "Deactivate/reassign cards through station-user card actions. Historical assignments must be retained.",
            },
        )

    from sqlalchemy import func

    deleted_rows = []
    affected_device_ids = sorted({int(item.device_id) for item in assignments})
    try:
        for item in assignments:
            event_count = db.query(func.count(AccessEvent.id)).filter(
                AccessEvent.device_id == item.device_id,
                AccessEvent.card_number == item.card_number,
            ).scalar() or 0
            deleted_rows.append({
                "assignment_id": item.id,
                "device_id": item.device_id,
                "card_number": item.card_number,
                "preserved_access_event_count": int(event_count),
            })
            db.delete(item)
        db.flush()
        for device_id in affected_device_ids:
            device = db.get(Device, device_id)
            if device is None:
                continue
            device.expected_card_count = db.query(func.count(StationCardAssignment.id)).filter(
                StationCardAssignment.device_id == device_id
            ).scalar() or 0
            device.observed_card_count = None
            device.inventory_status = "verification_required"
            device.last_inventory_at = None
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "deleted": True,
        "database_only": True,
        "controller_contacted": False,
        "controller_changed": False,
        "station_id": station_id,
        "deleted_count": len(deleted_rows),
        "deleted_assignments": deleted_rows,
        "affected_device_ids": affected_device_ids,
        "note": "Only orphaned cloud station-card rows were deleted. No Dahua connection or SDK command was made; access-event history was preserved.",
    }


@router.get("/stations/{station_id}/cards", response_model=list[StationCardRead])
def list_station_cards(
    station_id: int,
    active_only: bool = False,
    role: str | None = None,
    db: Session = Depends(get_db),
):
    _station_or_404(db, station_id)
    query = db.query(StationCardAssignment).filter(StationCardAssignment.station_id == station_id)
    if active_only:
        query = query.filter(StationCardAssignment.is_active.is_(True))
    assignments = query.order_by(StationCardAssignment.id.asc()).all()
    result = []
    for card in assignments:
        link = db.query(UserCardAssignment).filter(
            UserCardAssignment.station_card_assignment_id == card.id,
            UserCardAssignment.is_active.is_(True),
        ).first()
        station_user = db.get(StationUser, link.station_user_id) if link else None
        operational_role = db.get(OperationalRole, station_user.role_id) if station_user else None
        role_code = operational_role.code if operational_role else card.role
        if role and role_code.upper() != role.strip().upper() and card.role.upper() != role.strip().upper():
            continue
        item = {column.name: getattr(card, column.name) for column in StationCardAssignment.__table__.columns}
        item.update({
            "station_user_id": station_user.id if station_user else None,
            "station_user_name": station_user.name if station_user else None,
            "operational_role_code": operational_role.code if operational_role else None,
            "operational_role_name": operational_role.name if operational_role else None,
        })
        result.append(item)
    return result


@router.put("/stations/{station_id}/cards/{assignment_id}", response_model=StationCardRead)
def update_station_card(station_id: int, assignment_id: int, payload: StationCardUpdate, db: Session = Depends(get_db)):
    assignment = _assignment_or_404(db, station_id, assignment_id)
    values = payload.model_dump(exclude_unset=True)
    next_active = values.get("is_active", assignment.is_active)
    next_valid = values.get("is_valid", assignment.is_valid)
    if not next_active:
        next_valid = False
    if next_valid and not next_active:
        raise HTTPException(status_code=422, detail="An inactive card cannot be valid")

    card_type_value = assignment.card_type
    if values.get("card_type"):
        card_type_value = _card_type_value(values["card_type"])
    hardware_change = any(key in values for key in (
        "card_name", "card_type", "is_valid", "is_active", "valid_from", "valid_until",
        "door_indices", "time_section_indices",
    ))
    if hardware_change:
        device = _device_or_404(db, assignment.device_id)
        _ensure_connected(device, db)
        try:
            access_cards.update_device_card(
                assignment.device_id,
                int(assignment.device_record_no),
                original_card_number=assignment.card_number,
                card_number=assignment.card_number,
                card_name=values.get("card_name") or assignment.card_name,
                card_type=card_type_value,
                is_valid=next_valid,
                valid_from=values.get("valid_from") or assignment.valid_from,
                valid_until=values.get("valid_until") or assignment.valid_until,
                door_indices=values.get("door_indices") or assignment.door_indices,
                time_section_indices=values.get("time_section_indices") or assignment.time_section_indices,
            )
        except AccessCardSDKError as exc:
            assignment.sync_status = "failed"
            assignment.last_sync_error = str(exc)
            db.commit()
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    for key, value in values.items():
        if key == "card_type":
            assignment.card_type = card_type_value
        elif key in {"role", "card_name", "is_billable", "valid_from", "valid_until", "door_indices", "time_section_indices"}:
            setattr(assignment, key, value)
        elif key == "is_active":
            assignment.is_active = value
        elif key == "is_valid":
            assignment.is_valid = next_valid
    assignment.is_valid = next_valid
    assignment.device_card_status = 0 if next_valid else 4
    if hardware_change:
        assignment.sync_status = "pending_verification"
        assignment.last_sync_error = None
        assignment.last_synced_at = datetime.now(UTC)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/stations/{station_id}/cards/{assignment_id}")
def deactivate_station_card(station_id: int, assignment_id: int, db: Session = Depends(get_db)):
    """Soft-deactivate and freeze a card; keep the assignment for historical reports."""
    assignment = _assignment_or_404(db, station_id, assignment_id)
    if assignment.is_active or assignment.is_valid:
        device = _device_or_404(db, assignment.device_id)
        _ensure_connected(device, db)
        try:
            access_cards.update_device_card(
                assignment.device_id,
                int(assignment.device_record_no),
                original_card_number=assignment.card_number,
                card_number=assignment.card_number,
                card_name=assignment.card_name,
                card_type=assignment.card_type,
                is_valid=False,
                valid_from=assignment.valid_from or date.today(),
                valid_until=assignment.valid_until or date(2037, 12, 31),
                door_indices=assignment.door_indices or [0],
                time_section_indices=assignment.time_section_indices or [0],
            )
        except AccessCardSDKError as exc:
            assignment.sync_status = "failed"
            assignment.last_sync_error = str(exc)
            db.commit()
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    assignment.is_active = False
    assignment.is_valid = False
    assignment.device_card_status = 4
    assignment.sync_status = "pending_verification"
    assignment.last_sync_error = None
    assignment.last_synced_at = datetime.now(UTC)
    db.commit()
    return {"deactivated": True, "assignment_id": assignment_id, "station_id": station_id, "note": "The card assignment was retained for audit history and frozen on the controller request path."}


# --------------------------------- Pricing ---------------------------------

@router.post("/stations/{station_id}/rates", response_model=StationRateRead, status_code=status.HTTP_201_CREATED)
def create_station_rate(station_id: int, payload: StationRateCreate, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    existing_rates = db.query(StationRate).filter(
        StationRate.station_id == station_id,
        StationRate.role == payload.role,
    ).all()
    new_end = payload.effective_until or date.max
    for existing in existing_rates:
        old_end = existing.effective_until or date.max
        if payload.effective_from <= old_end and existing.effective_from <= new_end:
            raise HTTPException(
                status_code=409,
                detail=f"Rate period overlaps existing rate ID {existing.id}. Use non-overlapping effective dates.",
            )
    rate = StationRate(
        station_id=station_id,
        role=payload.role,
        rate_per_use=payload.rate_per_use,
        currency=payload.currency,
        effective_from=payload.effective_from,
        effective_until=payload.effective_until,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.get("/stations/{station_id}/rates", response_model=list[StationRateRead])
def list_station_rates(station_id: int, role: Literal["USER", "STAFF"] | None = None, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    query = db.query(StationRate).filter(StationRate.station_id == station_id)
    if role:
        query = query.filter(StationRate.role == role)
    return query.order_by(StationRate.role.asc(), StationRate.effective_from.asc()).all()


# ------------------------------- Collections -------------------------------

@router.post("/stations/{station_id}/cash-collections", response_model=CashCollectionRead, status_code=status.HTTP_201_CREATED)
def record_cash_collection(station_id: int, payload: CashCollectionCreate, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    collected_at = payload.collected_at or datetime.now(UTC)
    if collected_at.tzinfo is None:
        collected_at = collected_at.replace(tzinfo=PKT).astimezone(UTC)
    collection = CashCollection(
        station_id=station_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        amount=payload.amount,
        currency=payload.currency,
        collected_at=collected_at,
        received_by=payload.received_by,
        reference=payload.reference,
        notes=payload.notes,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.get("/stations/{station_id}/cash-collections", response_model=list[CashCollectionRead])
def list_cash_collections(station_id: int, start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    query = db.query(CashCollection).filter(CashCollection.station_id == station_id)
    if start_date:
        start_utc, _ = _local_report_bounds(start_date, start_date)
        query = query.filter(CashCollection.collected_at >= start_utc)
    if end_date:
        _, end_utc = _local_report_bounds(end_date, end_date)
        query = query.filter(CashCollection.collected_at < end_utc)
    return query.order_by(CashCollection.collected_at.desc(), CashCollection.id.desc()).all()


# ------------------------- Device inventory/recovery ------------------------

@router.post("/devices/{device_id}/inventory-check", response_model=InventoryCheckRead, tags=["Device Recovery"])
def check_device_inventory(device_id: int, db: Session = Depends(get_db)):
    device = _device_or_404(db, device_id)
    _ensure_connected(device, db)
    expected_assignments = db.query(StationCardAssignment).filter(
        StationCardAssignment.device_id == device_id
    ).order_by(StationCardAssignment.id.asc()).all()
    expected_numbers = {item.card_number.upper() for item in expected_assignments}
    now = datetime.now(UTC)
    try:
        rows = access_cards.list_device_cards(device_id)
    except AccessCardSDKError as exc:
        device.inventory_status = "unknown"
        device.last_inventory_at = now
        device.expected_card_count = len(expected_numbers)
        device.observed_card_count = None
        job = DeviceSyncJob(
            device_id=device_id,
            station_id=device.station_id,
            job_type="inventory_check",
            status="failed",
            expected_count=len(expected_numbers),
            error=str(exc),
            result={"interpretation": "Inventory is unknown. A failed SDK read is not evidence that the controller is empty."},
            completed_at=now,
        )
        db.add(job)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "inventory_status": "unknown",
                "expected_card_count": len(expected_numbers),
                "note": "No cloud records were changed. A read error must never be treated as an empty controller.",
            },
        ) from exc

    observed_numbers = {str(row.get("card_number") or "").upper() for row in rows if row.get("card_number")}
    # Repair stored record numbers from the controller so later updates/revokes hit the right record.
    record_by_card: dict[str, list[int]] = {}
    for row in rows:
        if row.get("card_number") and row.get("record_number") is not None:
            record_by_card.setdefault(str(row["card_number"]).upper(), []).append(int(row["record_number"]))
    repaired = []
    for item in expected_assignments:
        numbers = record_by_card.get(item.card_number.upper(), [])
        if len(numbers) == 1 and item.device_record_no != numbers[0]:
            item.device_record_no = numbers[0]
            repaired.append(item.card_number)
    missing = sorted(expected_numbers - observed_numbers)
    unexpected = sorted(observed_numbers - expected_numbers)
    inventory_status = "needs_reprovisioning" if missing else ("in_sync" if not unexpected else "in_sync_with_unexpected_records")
    device.inventory_status = inventory_status
    device.last_inventory_at = now
    device.expected_card_count = len(expected_numbers)
    device.observed_card_count = len(observed_numbers)
    check_job = DeviceSyncJob(
        device_id=device_id,
        station_id=device.station_id,
        job_type="inventory_check",
        status="succeeded",
        expected_count=len(expected_numbers),
        observed_count=len(observed_numbers),
        missing_cards=missing,
        unexpected_cards=unexpected,
        result={"inventory_status": inventory_status, "repaired_record_numbers": repaired},
        completed_at=now,
    )
    db.add(check_job)
    db.flush()
    reprovision_job_id = None
    if missing:
        pending = DeviceSyncJob(
            device_id=device_id,
            station_id=device.station_id,
            job_type="reprovision",
            status="pending",
            expected_count=len(expected_numbers),
            observed_count=len(observed_numbers),
            missing_cards=missing,
            unexpected_cards=unexpected,
            result={"reason": "Cloud inventory contains card assignments missing from the readable controller inventory."},
        )
        db.add(pending)
        db.flush()
        reprovision_job_id = pending.id
    db.commit()
    return {
        "device_id": device_id,
        "station_id": device.station_id,
        "inventory_status": inventory_status,
        "expected_count": len(expected_numbers),
        "observed_count": len(observed_numbers),
        "missing_cards": missing,
        "unexpected_cards": unexpected,
        "sync_job_id": check_job.id,
        "reprovision_job_id": reprovision_job_id,
        "repaired_record_numbers": repaired,
        "note": "Unexpected records are reported but never deleted automatically. Use the separate confirmed reprovision action only after reviewing the comparison.",
    }


@router.post("/devices/{device_id}/reprovision", tags=["Device Recovery"])
def reprovision_device_from_cloud(
    device_id: int,
    payload: ReprovisionRequest,
    db: Session = Depends(get_db),
):
    device = _device_or_404(db, device_id)
    confirmed_factory_reset = bool(payload.controller_confirmed_factory_reset)
    latest_reprovision = db.query(DeviceSyncJob).filter(
        DeviceSyncJob.device_id == device_id,
        DeviceSyncJob.job_type == "reprovision",
    ).order_by(DeviceSyncJob.id.desc()).first()
    if (
        confirmed_factory_reset
        and latest_reprovision is not None
        and latest_reprovision.status in {"running", "failed", "verification_required"}
        and bool((latest_reprovision.result or {}).get("factory_reset_confirmed"))
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "An administrator-confirmed restore attempt has already written to this controller. "
                "Do not repeat the request because the ASI1201E inventory read may be unsupported and "
                "repeating inserts could create duplicate card records. Check SmartPSS and test every "
                "card; if all are present and work, use the manual-verification endpoint."
            ),
        )
    if device.inventory_status != "needs_reprovisioning" and not (
        device.inventory_status == "unknown" and confirmed_factory_reset
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Run a successful inventory check first, or set "
                "controller_confirmed_factory_reset=true only after an administrator has physically confirmed a factory reset."
            ),
        )
    job = db.query(DeviceSyncJob).filter(
        DeviceSyncJob.device_id == device_id,
        DeviceSyncJob.job_type == "reprovision",
        DeviceSyncJob.status == "pending",
    ).order_by(DeviceSyncJob.id.desc()).first()
    if job is None:
        if not confirmed_factory_reset:
            raise HTTPException(status_code=409, detail="No pending reprovision job exists for this device")
        job = DeviceSyncJob(
            device_id=device_id,
            station_id=device.station_id,
            job_type="reprovision",
            status="pending",
            expected_count=0,
            result={"reason": "Administrator confirmed a factory reset and requested restoration from the cloud."},
        )
        db.add(job)
        db.flush()

    _ensure_connected(device, db)
    expected = db.query(StationCardAssignment).filter(
        StationCardAssignment.device_id == device_id
    ).order_by(StationCardAssignment.id.asc()).all()
    if not expected:
        raise HTTPException(status_code=409, detail="No station card assignments exist in the cloud database for this device")

    if confirmed_factory_reset:
        # Explicit administrative confirmation is the only path that skips the
        # device inventory preflight. It is intended for a known-empty controller
        # after a factory reset, not for routine synchronization.
        missing = list(expected)
        job.result = {
            "factory_reset_confirmed": True,
            "reason": "Factory reset confirmed by administrator; controller assumed empty for provisioning.",
        }
    else:
        try:
            current_rows = access_cards.list_device_cards(device_id)
        except AccessCardSDKError as exc:
            device.inventory_status = "unknown"
            job.status = "failed"
            job.error = f"Could not verify current controller inventory before writing: {exc}"
            job.completed_at = datetime.now(UTC)
            db.commit()
            raise HTTPException(status_code=502, detail=job.error) from exc
        present = {str(row.get("card_number") or "").upper() for row in current_rows if row.get("card_number")}
        missing = [item for item in expected if item.card_number.upper() not in present]

    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.expected_count = len(expected)
    job.missing_cards = [item.card_number for item in missing]
    device.inventory_status = "reprovisioning"
    db.commit()

    restored: list[str] = []
    failures: list[dict] = []
    for item in missing:
        try:
            record_no = access_cards.add_device_card(
                device_id,
                card_number=item.card_number,
                card_name=item.card_name,
                card_type=item.card_type,
                is_valid=bool(item.is_valid and item.is_active),
                valid_from=item.valid_from or date.today(),
                valid_until=item.valid_until or date(2037, 12, 31),
                door_indices=item.door_indices or [0],
                time_section_indices=item.time_section_indices or [0],
                skip_duplicate_check=confirmed_factory_reset,
            )
            item.device_record_no = record_no
            item.device_card_status = 0 if item.is_valid and item.is_active else 4
            item.sync_status = "pending_verification"
            item.last_sync_error = None
            item.last_synced_at = datetime.now(UTC)
            restored.append(item.card_number)
        except AccessCardSDKError as exc:
            item.sync_status = "failed"
            item.last_sync_error = str(exc)
            failures.append({"card_number": item.card_number, "error": str(exc)})
    db.commit()

    try:
        verification_rows = access_cards.list_device_cards(device_id)
        verified = {str(row.get("card_number") or "").upper() for row in verification_rows if row.get("card_number")}
        still_missing = sorted({item.card_number.upper() for item in expected} - verified)
        device.last_inventory_at = datetime.now(UTC)
        device.expected_card_count = len(expected)
        device.observed_card_count = len(verified)
        if still_missing or failures:
            device.inventory_status = "needs_reprovisioning"
            job.status = "failed"
            job.error = "Some cloud card records could not be restored or verified."
        else:
            device.inventory_status = "in_sync"
            job.status = "succeeded"
            for item in expected:
                item.sync_status = "synced"
                item.last_sync_error = None
                item.last_synced_at = datetime.now(UTC)
        job.missing_cards = still_missing
        job.result = {
            "factory_reset_confirmed": confirmed_factory_reset,
            "restored_cards": restored,
            "failed_cards": failures,
            "verified_count": len(verified),
            "unexpected_cards": sorted(verified - {item.card_number.upper() for item in expected}),
        }
        job.observed_count = len(verified)
        job.completed_at = datetime.now(UTC)
        db.commit()
        return {
            "device_id": device_id,
            "job_id": job.id,
            "status": job.status,
            "restored_cards": restored,
            "failed_cards": failures,
            "still_missing_cards": still_missing,
            "inventory_status": device.inventory_status,
            "note": "A card is marked synced only after a successful controller inventory read confirms it is present.",
        }
    except AccessCardSDKError as exc:
        device.inventory_status = "verification_required"
        job.status = "verification_required"
        job.error = str(exc)
        job.result = {
            "factory_reset_confirmed": confirmed_factory_reset,
            "restored_cards": restored,
            "failed_cards": failures,
        }
        job.completed_at = datetime.now(UTC)
        for item in expected:
            if item.card_number in restored:
                item.sync_status = "pending_verification"
                item.last_sync_error = "Controller accepted the write, but inventory readback is not available."
        db.commit()
        return {
            "device_id": device_id,
            "job_id": job.id,
            "status": job.status,
            "restored_cards": restored,
            "failed_cards": failures,
            "inventory_status": device.inventory_status,
            "verification_error": str(exc),
            "note": "The SDK accepted the writes, but readback failed. The system deliberately does not claim that the records are synced.",
        }


@router.post(
    "/devices/{device_id}/reprovision/manual-verification",
    tags=["Device Recovery"],
    summary="Confirm cards manually when controller inventory readback is unsupported",
    description=(
        "Use only after an administrator has checked every expected card in SmartPSS/device management "
        "and physically tested access with each card. The supplied card-number list must exactly match "
        "the cloud assignments. This closes a verification-required restore job without pretending that "
        "the unsupported SDK inventory API succeeded."
    ),
)
def confirm_manual_reprovision_verification(
    device_id: int,
    payload: ManualReprovisionVerificationRequest,
    db: Session = Depends(get_db),
):
    device = _device_or_404(db, device_id)
    job = db.query(DeviceSyncJob).filter(
        DeviceSyncJob.device_id == device_id,
        DeviceSyncJob.job_type == "reprovision",
        DeviceSyncJob.status == "verification_required",
    ).order_by(DeviceSyncJob.id.desc()).first()
    if job is None:
        raise HTTPException(status_code=409, detail="No restore job is waiting for manual verification")

    assignments = db.query(StationCardAssignment).filter(
        StationCardAssignment.device_id == device_id
    ).order_by(StationCardAssignment.id.asc()).all()
    expected_numbers = {item.card_number.upper() for item in assignments}
    verified_numbers = set(payload.verified_card_numbers)
    missing = sorted(expected_numbers - verified_numbers)
    unexpected = sorted(verified_numbers - expected_numbers)
    if missing or unexpected:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "The manually verified card list must exactly match all cloud station assignments.",
                "missing_cards": missing,
                "unexpected_cards": unexpected,
            },
        )

    without_record_number = [item.card_number for item in assignments if item.device_record_no is None]
    if without_record_number:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Some card inserts did not return a controller record number; manual verification cannot finalize these assignments.",
                "cards_without_device_record_number": without_record_number,
            },
        )

    now = datetime.now(UTC)
    for item in assignments:
        item.sync_status = "synced"
        item.last_sync_error = None
        item.last_synced_at = now
    device.inventory_status = "in_sync"
    device.last_inventory_at = now
    device.expected_card_count = len(assignments)
    device.observed_card_count = len(verified_numbers)
    job.status = "succeeded"
    job.observed_count = len(verified_numbers)
    job.error = None
    job.result = {
        **(job.result or {}),
        "verification_method": "manual_smartpss_review_and_physical_card_access_test",
        "manually_verified_card_numbers": sorted(verified_numbers),
        "manual_verification_at": now.isoformat(),
        "note": "An administrator confirmed every card in the device management interface and tested each physical card. SDK inventory readback remains unsupported/unavailable.",
    }
    job.completed_at = now
    db.commit()
    return {
        "device_id": device_id,
        "job_id": job.id,
        "status": job.status,
        "inventory_status": device.inventory_status,
        "verified_card_numbers": sorted(verified_numbers),
        "verification_method": "manual_smartpss_review_and_physical_card_access_test",
        "note": "The administrator's manual verification was recorded. This does not mean the SDK inventory readback API is supported.",
    }


@router.get("/devices/{device_id}/sync-jobs", tags=["Device Recovery"])
def list_device_sync_jobs(
    device_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _device_or_404(db, device_id)
    jobs = db.query(DeviceSyncJob).filter(
        DeviceSyncJob.device_id == device_id
    ).order_by(DeviceSyncJob.id.desc()).limit(limit).all()
    return [
        {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "expected_count": job.expected_count,
            "observed_count": job.observed_count,
            "missing_cards": job.missing_cards,
            "unexpected_cards": job.unexpected_cards,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }
        for job in jobs
    ]


# -------------------------------- Reporting ---------------------------------

@router.get("/dashboard/summary", tags=["Dashboard and Reports"])
def dashboard_summary(
    station_id: int | None = Query(default=None, gt=0),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    today = datetime.now(PKT).date()
    start = start_date or (today - timedelta(days=29))
    end = end_date or today
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if station_id is not None:
        _station_or_404(db, station_id)
    return _summary_for_range(db, station_id, start, end)


@router.get("/dashboard/stations", tags=["Dashboard and Reports"])
def dashboard_station_overview(
    station_id: int | None = Query(default=None, gt=0),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    today = datetime.now(PKT).date()
    start = start_date or (today - timedelta(days=29))
    end = end_date or today
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    stations_query = db.query(Station)
    if station_id is not None:
        _station_or_404(db, station_id)
        stations_query = stations_query.filter(Station.id == station_id)
    stations = stations_query.order_by(Station.station_code.asc()).all()
    result = []
    for station in stations:
        devices = db.query(Device).filter(Device.station_id == station.id).all()
        assignments = db.query(StationCardAssignment).filter(
            StationCardAssignment.station_id == station.id
        ).all()
        active_links = db.query(UserCardAssignment).filter(
            UserCardAssignment.station_id == station.id,
            UserCardAssignment.is_active.is_(True),
        ).all()
        role_card_counts: dict[str, int] = {}
        linked_card_ids = {link.station_card_assignment_id for link in active_links}
        legacy_unlinked_user_cards = sum(1 for item in assignments if item.is_active and item.role == "USER" and item.id not in linked_card_ids)
        legacy_unlinked_staff_cards = sum(1 for item in assignments if item.is_active and item.role == "STAFF" and item.id not in linked_card_ids)
        for link in active_links:
            linked_user = db.get(StationUser, link.station_user_id)
            linked_role = db.get(OperationalRole, linked_user.role_id) if linked_user else None
            if linked_role is not None:
                role_card_counts[linked_role.code] = role_card_counts.get(linked_role.code, 0) + 1
        summary = _summary_for_range(db, station.id, start, end)
        result.append({
            "station_id": station.id,
            "station_code": station.station_code,
            "station_name": station.name,
            "city": station.city,
            "is_active": station.is_active,
            "device_count": len(devices),
            "online_devices": sum(1 for device in devices if device.status == "online"),
            "devices_needing_attention": sum(1 for device in devices if device.inventory_status in {"needs_reprovisioning", "verification_required", "unknown"}),
            "total_cards": len(assignments),
            "active_cards": sum(1 for item in assignments if item.is_active),
            "user_cards": role_card_counts.get("CUSTOMER", 0) + legacy_unlinked_user_cards,
            "customer_cards": role_card_counts.get("CUSTOMER", 0),
            "staff_cards": role_card_counts.get("STAFF", 0) + legacy_unlinked_staff_cards,
            "manager_cards": role_card_counts.get("MANAGER", 0),
            "admin_cards": role_card_counts.get("ADMIN", 0),
            "custom_role_card_counts": {code: count for code, count in role_card_counts.items() if code not in {"CUSTOMER", "STAFF", "MANAGER", "ADMIN"}},
            "usage": summary,
        })
    return {"start_date": start, "end_date": end, "station_count": len(result), "items": result}


@router.get("/reports/usage", tags=["Dashboard and Reports"])
def usage_report(
    group_by: Literal["day", "week", "month", "year"] = "day",
    station_id: int | None = Query(default=None, gt=0),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    today = datetime.now(PKT).date()
    start = start_date or (today - timedelta(days=29))
    end = end_date or today
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if station_id is not None:
        _station_or_404(db, station_id)
    events = _report_query(db, station_id=station_id, start_date=start, end_date=end).all()
    buckets: dict[str, dict] = {}
    for event in events:
        local_day = _event_date_local(event)
        if group_by == "day":
            key = local_day.isoformat()
        elif group_by == "week":
            iso = local_day.isocalendar()
            key = f"{iso.year}-W{iso.week:02d}"
        elif group_by == "month":
            key = local_day.strftime("%Y-%m")
        else:
            key = str(local_day.year)
        row = buckets.setdefault(key, {
            "period": key, "total_scans": 0, "granted_scans": 0, "denied_scans": 0,
            "user_entries": 0, "staff_entries": 0, "billable_entries": 0,
            "unpriced_billable_entries": 0, "expected_collection": Decimal("0.00"),
        })
        row["total_scans"] += 1
        row["granted_scans"] += int(event.access_result == "granted")
        row["denied_scans"] += int(event.access_result == "denied")
        entry_granted = event.access_result == "granted" and event.event_direction.upper() == "ENTRY"
        row["user_entries"] += int(entry_granted and event.card_role in {"USER", "CUSTOMER"})
        row["staff_entries"] += int(entry_granted and event.card_role == "STAFF")
        if event.is_billable:
            row["billable_entries"] += 1
            if event.rate_applied is None:
                row["unpriced_billable_entries"] += 1
            else:
                row["expected_collection"] += _money(event.rate_applied)
    return {
        "station_id": station_id,
        "group_by": group_by,
        "start_date": start,
        "end_date": end,
        "currency": "PKR",
        "items": [buckets[key] for key in sorted(buckets)],
    }


@router.get("/reports/card-usage", tags=["Dashboard and Reports"])
def card_usage_report(
    station_id: int | None = Query(default=None, gt=0),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    today = datetime.now(PKT).date()
    start = start_date or (today - timedelta(days=29))
    end = end_date or today
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if station_id is not None:
        _station_or_404(db, station_id)
    events = _report_query(db, station_id=station_id, start_date=start, end_date=end).all()
    groups: dict[tuple, dict] = {}
    for event in events:
        if not event.card_number:
            continue
        key = (event.station_id, event.station_name, event.card_number, event.card_role)
        row = groups.setdefault(key, {
            "station_id": event.station_id, "station_name": event.station_name,
            "card_number": event.card_number, "role": event.card_role,
            "total_scans": 0, "granted_scans": 0, "denied_scans": 0,
            "granted_entries": 0, "billable_entries": 0, "expected_collection": Decimal("0.00"),
        })
        row["total_scans"] += 1
        row["granted_scans"] += int(event.access_result == "granted")
        row["denied_scans"] += int(event.access_result == "denied")
        entry = event.access_result == "granted" and event.event_direction.upper() == "ENTRY"
        row["granted_entries"] += int(entry)
        if event.is_billable:
            row["billable_entries"] += 1
            row["expected_collection"] += _money(event.rate_applied)
    return {
        "station_id": station_id,
        "start_date": start,
        "end_date": end,
        "currency": "PKR",
        "items": sorted(groups.values(), key=lambda row: (row["station_id"] or 0, row["card_number"])),
    }
