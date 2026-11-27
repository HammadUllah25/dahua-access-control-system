from __future__ import annotations

from datetime import date, datetime, timezone
import re
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.device import Device
from app.models.station import Station
from app.models.station_card_assignment import StationCardAssignment
from app.models.operational_role import OperationalRole
from app.models.station_user import StationUser
from app.models.user_card_assignment import UserCardAssignment
from app.models.access_card import AccessCard
from app.schemas.card_enrollment import CardEnrollmentRead
from app.schemas.station_users import (
    OperationalRoleCreate, OperationalRoleUpdate, OperationalRoleRead,
    StationUserCreate, StationUserUpdate, StationUserRead,
    StationUserCardEnrollmentStart, StationUserCardEnrollmentConfirm,
    AdoptStationCardRequest, UserCardAssignmentRead,
)
from app.services.card_enrollment import enrollment_service, CardEnrollmentError
from app.services.access_cards import access_cards, AccessCardSDKError
from app.services.device_sessions import sessions
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError

router = APIRouter(tags=["Station Users and Operational Roles"])
UTC = timezone.utc
PKT = ZoneInfo("Asia/Karachi")
CARD_TYPE_MAP = {"general": 0, "vip": 1, "guest": 2}
SYSTEM_ROLE_DEFAULTS = (
    ("MANAGER", "Manager", "Station manager", False),
    ("ADMIN", "Admin", "Station administrator", False),
    ("STAFF", "Staff", "Station staff member", False),
    ("CUSTOMER", "Customer", "Washroom customer", True),
)


def _station_or_404(db: Session, station_id: int) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


def _user_or_404(db: Session, station_id: int, user_id: int) -> StationUser:
    user = db.query(StationUser).filter(
        StationUser.id == user_id, StationUser.station_id == station_id
    ).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Station user not found")
    return user


def _role_for_station(db: Session, station_id: int, role_id: int, *, active: bool = True) -> OperationalRole:
    query = db.query(OperationalRole).filter(
        OperationalRole.id == role_id,
        (OperationalRole.station_id.is_(None) | (OperationalRole.station_id == station_id)),
    )
    if active:
        query = query.filter(OperationalRole.is_active.is_(True))
    role = query.first()
    if role is None:
        raise HTTPException(status_code=422, detail="Selected role is not available for this station")
    return role


def _device_for_station(db: Session, station_id: int, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Dahua device not found")
    if device.station_id != station_id:
        raise HTTPException(status_code=409, detail="The selected Dahua device is not assigned to this station")
    return device


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


def _active_user_assignment(db: Session, user_id: int) -> UserCardAssignment | None:
    return db.query(UserCardAssignment).filter(
        UserCardAssignment.station_user_id == user_id,
        UserCardAssignment.is_active.is_(True),
    ).first()


def _user_read(db: Session, user: StationUser) -> dict:
    role = user.operational_role
    link = _active_user_assignment(db, user.id)
    active_card = None
    if link is not None:
        card = db.get(StationCardAssignment, link.station_card_assignment_id)
        if card is not None:
            active_card = {
                "id": link.id,
                "station_card_assignment_id": card.id,
                "device_id": card.device_id,
                "card_number": card.card_number,
                "card_name": card.card_name,
                "sync_status": card.sync_status,
                "is_valid": card.is_valid,
                "valid_from": card.valid_from,
                "valid_until": card.valid_until,
                "assigned_at": link.assigned_at,
            }
    effective_billable = (
        user.is_billable_override
        if user.is_billable_override is not None
        else bool(role.default_is_billable)
    )
    return {
        "id": user.id,
        "station_id": user.station_id,
        "name": user.name,
        "phone": user.phone,
        "role": role,
        "is_billable": effective_billable,
        "is_billable_override": user.is_billable_override,
        "is_active": user.is_active,
        "active_card": active_card,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _ensure_no_active_user_card(db: Session, user: StationUser) -> None:
    if _active_user_assignment(db, user.id) is not None:
        raise HTTPException(status_code=409, detail="This user already has an active RFID card. Deactivate it before assigning another card.")


def _ensure_card_not_assigned(db: Session, card_number: str) -> None:
    active = db.query(UserCardAssignment).filter(
        UserCardAssignment.card_number == card_number,
        UserCardAssignment.is_active.is_(True),
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="This RFID card is already assigned to another station user")


def _card_assignment_read(link: UserCardAssignment) -> dict:
    return {
        "id": link.id,
        "station_user_id": link.station_user_id,
        "station_card_assignment_id": link.station_card_assignment_id,
        "station_id": link.station_id,
        "device_id": link.device_id,
        "card_number": link.card_number,
        "is_active": link.is_active,
        "assigned_at": link.assigned_at,
        "ended_at": link.ended_at,
    }


@router.get("/stations/{station_id}/roles", response_model=list[OperationalRoleRead])
def list_operational_roles(station_id: int, include_inactive: bool = False, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    query = db.query(OperationalRole).filter(
        OperationalRole.station_id.is_(None) | (OperationalRole.station_id == station_id)
    )
    if not include_inactive:
        query = query.filter(OperationalRole.is_active.is_(True))
    return query.order_by(OperationalRole.is_system.desc(), OperationalRole.name.asc()).all()


@router.post("/stations/{station_id}/roles", response_model=OperationalRoleRead, status_code=status.HTTP_201_CREATED)
def create_operational_role(station_id: int, payload: OperationalRoleCreate, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    code = payload.code or re.sub(r"[^A-Z0-9]+", "_", payload.name.upper()).strip("_")
    code = code[:20]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,23}", code):
        raise HTTPException(status_code=422, detail="Role code must start with a letter and contain only letters, numbers and underscores")
    if code in {item[0] for item in SYSTEM_ROLE_DEFAULTS}:
        raise HTTPException(status_code=409, detail="This is a predefined role and cannot be recreated as a custom role")
    existing = db.query(OperationalRole).filter(
        OperationalRole.station_id == station_id,
        OperationalRole.code == code,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A role with this code already exists at the station")
    role = OperationalRole(
        station_id=station_id,
        code=code,
        name=payload.name,
        description=payload.description,
        is_system=False,
        default_is_billable=payload.default_is_billable,
        is_active=True,
    )
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A role with this code already exists at the station") from exc
    db.refresh(role)
    return role


@router.patch("/stations/{station_id}/roles/{role_id}", response_model=OperationalRoleRead)
def update_operational_role(station_id: int, role_id: int, payload: OperationalRoleUpdate, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    role = db.query(OperationalRole).filter(
        OperationalRole.id == role_id,
        (OperationalRole.station_id.is_(None) | (OperationalRole.station_id == station_id)),
    ).first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found for this station")
    if role.is_system:
        raise HTTPException(status_code=409, detail="Predefined roles cannot be modified")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, key, value)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/stations/{station_id}/roles/{role_id}")
def deactivate_operational_role(station_id: int, role_id: int, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    role = db.query(OperationalRole).filter(
        OperationalRole.id == role_id,
        (OperationalRole.station_id.is_(None) | (OperationalRole.station_id == station_id)),
    ).first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found for this station")
    if role.is_system:
        raise HTTPException(status_code=409, detail="Predefined roles cannot be deactivated")
    role.is_active = False
    db.commit()
    return {"deactivated": True, "role_id": role.id}


@router.post("/stations/{station_id}/users", response_model=StationUserRead, status_code=status.HTTP_201_CREATED)
def create_station_user(station_id: int, payload: StationUserCreate, db: Session = Depends(get_db)):
    station = _station_or_404(db, station_id)
    if not station.is_active:
        raise HTTPException(status_code=409, detail="Cannot register users at an inactive station")
    role = _role_for_station(db, station_id, payload.role_id)
    user = StationUser(
        station_id=station_id,
        name=payload.name,
        phone=payload.phone,
        role_id=role.id,
        is_billable_override=payload.is_billable,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_read(db, user)


@router.get("/stations/{station_id}/users", response_model=list[StationUserRead])
def list_station_users(station_id: int, active_only: bool = False, role_id: int | None = None, db: Session = Depends(get_db)):
    _station_or_404(db, station_id)
    query = db.query(StationUser).filter(StationUser.station_id == station_id)
    if active_only:
        query = query.filter(StationUser.is_active.is_(True))
    if role_id is not None:
        query = query.filter(StationUser.role_id == role_id)
    users = query.order_by(StationUser.id.asc()).all()
    return [_user_read(db, user) for user in users]


@router.get("/stations/{station_id}/users/{user_id}", response_model=StationUserRead)
def get_station_user(station_id: int, user_id: int, db: Session = Depends(get_db)):
    return _user_read(db, _user_or_404(db, station_id, user_id))


@router.patch("/stations/{station_id}/users/{user_id}", response_model=StationUserRead)
def update_station_user(station_id: int, user_id: int, payload: StationUserUpdate, db: Session = Depends(get_db)):
    user = _user_or_404(db, station_id, user_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("role_id") is not None:
        _role_for_station(db, station_id, values["role_id"])
        user.role_id = values.pop("role_id")
    if values.get("is_active") is False and _active_user_assignment(db, user.id) is not None:
        raise HTTPException(status_code=409, detail="Deactivate the user's RFID card before deactivating the user")
    clear_billable_override = values.pop("clear_billable_override", False)
    if clear_billable_override:
        user.is_billable_override = None
        values.pop("is_billable", None)
    elif "is_billable" in values:
        user.is_billable_override = values.pop("is_billable")
    for key, value in values.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return _user_read(db, user)


@router.delete("/stations/{station_id}/users/{user_id}")
def delete_station_user(station_id: int, user_id: int, db: Session = Depends(get_db)):
    user = _user_or_404(db, station_id, user_id)
    if _active_user_assignment(db, user.id) is not None:
        raise HTTPException(status_code=409, detail="Revoke the user's RFID card before deleting the user")
    # Inactive card-history links block the delete (FK RESTRICT); remove them with the user.
    db.query(UserCardAssignment).filter(UserCardAssignment.station_user_id == user.id).delete(synchronize_session=False)
    name = user.name
    db.delete(user)
    db.commit()
    return {"deleted": True, "station_user_id": user_id, "name": name}


@router.post("/stations/{station_id}/users/{user_id}/cards/adopt", response_model=UserCardAssignmentRead, status_code=status.HTTP_201_CREATED)
def adopt_existing_station_card(station_id: int, user_id: int, payload: AdoptStationCardRequest, db: Session = Depends(get_db)):
    user = _user_or_404(db, station_id, user_id)
    if not user.is_active:
        raise HTTPException(status_code=409, detail="Cannot assign a card to an inactive user")
    _ensure_no_active_user_card(db, user)
    card = db.query(StationCardAssignment).filter(
        StationCardAssignment.id == payload.station_card_assignment_id,
        StationCardAssignment.station_id == station_id,
    ).first()
    if card is None:
        raise HTTPException(status_code=404, detail="Station card assignment not found")
    if not card.is_active:
        raise HTTPException(status_code=409, detail="Cannot adopt an inactive station card")
    device = _device_for_station(db, station_id, card.device_id)
    _ensure_card_not_assigned(db, card.card_number)
    # Linking a cloud record is not proof that the physical controller still
    # contains it. Require a new access/inventory verification after adoption.
    card.sync_status = "pending_verification"
    card.last_sync_error = "Linked to a named station user; verify the controller record and physical access before marking synchronized."
    device.inventory_status = "verification_required"
    device.last_inventory_at = None
    device.observed_card_count = None
    link = UserCardAssignment(
        station_user_id=user.id,
        station_card_assignment_id=card.id,
        station_id=station_id,
        device_id=device.id,
        card_number=card.card_number,
        is_active=True,
    )
    db.add(link)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This user or RFID card already has an active card assignment") from exc
    db.refresh(link)
    return _card_assignment_read(link)


@router.post("/stations/{station_id}/users/{user_id}/card-enrollments", response_model=CardEnrollmentRead, status_code=status.HTTP_202_ACCEPTED)
def begin_station_user_card_enrollment(station_id: int, user_id: int, payload: StationUserCardEnrollmentStart, db: Session = Depends(get_db)):
    user = _user_or_404(db, station_id, user_id)
    if not user.is_active:
        raise HTTPException(status_code=409, detail="Cannot enroll a card for an inactive user")
    _ensure_no_active_user_card(db, user)
    device = _device_for_station(db, station_id, payload.device_id)
    _ensure_connected(device, db)
    session = sessions.get_session(device.id)
    if session is None or not session.alarm_listening:
        if session is not None:
            sessions.disconnect(device.id)
        _ensure_connected(device, db)
        session = sessions.get_session(device.id)
    if session is None or not session.alarm_listening:
        detail = session.subscription_error if session else "No active SDK login"
        raise HTTPException(status_code=503, detail=f"Dahua card-scan listener is not active: {detail or 'unknown error'}")
    try:
        return enrollment_service.begin_for_user(device.id, station_id, user.id, payload.timeout_seconds)
    except CardEnrollmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/stations/{station_id}/users/{user_id}/card-enrollments/{session_token}", response_model=CardEnrollmentRead)
def get_station_user_card_enrollment(station_id: int, user_id: int, session_token: str, db: Session = Depends(get_db)):
    _user_or_404(db, station_id, user_id)
    result = enrollment_service.get_for_station_user(session_token) if hasattr(enrollment_service, "get_for_station_user") else None
    if result is None or result.get("station_id") != station_id or result.get("station_user_id") != user_id:
        raise HTTPException(status_code=404, detail="Enrollment session not found or does not belong to this station user")
    if result["device_id"]:
        device = db.get(Device, result["device_id"])
        if device is None or device.station_id != station_id:
            raise HTTPException(status_code=404, detail="Enrollment session device is not assigned to this station")
    return result


@router.post("/stations/{station_id}/users/{user_id}/card-enrollments/{session_token}/confirm", status_code=status.HTTP_201_CREATED)
def confirm_station_user_card_enrollment(station_id: int, user_id: int, session_token: str, payload: StationUserCardEnrollmentConfirm, db: Session = Depends(get_db)):
    user = _user_or_404(db, station_id, user_id)
    if not user.is_active:
        raise HTTPException(status_code=409, detail="Cannot assign a card to an inactive user")
    _ensure_no_active_user_card(db, user)
    try:
        enrollment = enrollment_service.claim_for_confirmation_for_user(session_token, station_id, user_id)
    except AttributeError:
        raise HTTPException(status_code=500, detail="Card enrollment service is missing station-user ownership support")
    except CardEnrollmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    card_number = (enrollment.card_number or "").strip().upper()
    try:
        device = _device_for_station(db, station_id, enrollment.device_id)
        _ensure_card_not_assigned(db, card_number)
        existing = db.query(StationCardAssignment).filter(StationCardAssignment.card_number == card_number).first()
        # A removed (inactive) card on this station's controller can be given to a new user;
        # anything else stays blocked so an in-use or foreign card is never taken over.
        if existing is not None and (
            existing.is_active
            or existing.station_id != station_id
            or existing.device_id != device.id
            or existing.device_record_no is None
        ):
            raise HTTPException(status_code=409, detail="This RFID card is still active or belongs to another controller; remove it from its current owner first")
        if db.query(AccessCard).filter(AccessCard.card_number == card_number).first():
            raise HTTPException(status_code=409, detail="This RFID card is already registered through the legacy card workflow")
        _ensure_connected(device, db)
        role = user.operational_role
        effective_billable = user.is_billable_override if user.is_billable_override is not None else role.default_is_billable
        legacy_role = "USER" if effective_billable else "STAFF"
        # The physical card UID is the default display name; the station user's name remains stored separately in StationUser.
        card_name = payload.card_name or card_number
        if len(card_name.encode("utf-8")) > 63:
            raise HTTPException(status_code=422, detail="Card display name must fit within 63 UTF-8 bytes; provide a shorter card_name")
        card_fields = dict(
            card_name=card_name,
            role=legacy_role,
            is_billable=bool(effective_billable),
            is_active=True,
            card_type=CARD_TYPE_MAP[payload.card_type],
            device_card_status=0 if payload.is_valid else 4,
            is_valid=payload.is_valid,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            door_indices=payload.door_indices,
            time_section_indices=payload.time_section_indices,
            sync_status="pending_verification",
            last_synced_at=datetime.now(UTC),
        )
        controller_fields = dict(
            card_number=card_number,
            card_name=card_name,
            card_type=CARD_TYPE_MAP[payload.card_type],
            is_valid=payload.is_valid,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            door_indices=payload.door_indices,
            time_section_indices=payload.time_section_indices,
        )
        if existing is not None:
            # Re-enable the same controller record under the new owner instead of inserting a duplicate.
            reused_record = int(existing.device_record_no)
            actual_record = access_cards.update_device_card(device.id, reused_record, original_card_number=existing.card_number, **controller_fields)
            card = existing
            if actual_record is not None:
                card.device_record_no = reused_record = actual_record
            for field, value in card_fields.items():
                setattr(card, field, value)
            card.last_sync_error = "Removed card was reassigned and re-enabled; verify it through controller inventory before marking synchronized."
        else:
            record_number = access_cards.add_device_card(device.id, **controller_fields)
            card = StationCardAssignment(
                station_id=station_id,
                device_id=device.id,
                card_number=card_number,
                device_record_no=record_number,
                last_sync_error="Card was inserted; verify it through controller inventory before marking synchronized.",
                **card_fields,
            )
            db.add(card)
        db.flush()
        link = UserCardAssignment(
            station_user_id=user.id,
            station_card_assignment_id=card.id,
            station_id=station_id,
            device_id=device.id,
            card_number=card_number,
            is_active=True,
        )
        db.add(link)
        db.commit()
        db.refresh(card)
        enrollment_service.confirmation_succeeded_for_user(session_token)
        return {
            "message": "RFID card registered on the Dahua controller and assigned to the station user. Controller readback verification is still required.",
            "station_user_id": user.id,
            "station_user_name": user.name,
            "role": role.code,
            "is_billable": bool(effective_billable),
            "card": {
                "id": card.id,
                "station_card_assignment_id": card.id,
                "device_id": card.device_id,
                "card_number": card.card_number,
                "card_name": card.card_name,
                "sync_status": card.sync_status,
                "is_valid": card.is_valid,
                "valid_from": card.valid_from,
                "valid_until": card.valid_until,
                "assigned_at": link.assigned_at,
            },
        }
    except HTTPException:
        db.rollback()
        enrollment_service.confirmation_failed_for_user(session_token)
        raise
    except (AccessCardSDKError, IntegrityError) as exc:
        db.rollback()
        if "record_number" in locals():
            try:
                access_cards.delete_device_card(device.id, record_number)
            except AccessCardSDKError:
                pass
        if "reused_record" in locals():
            try:
                access_cards.update_device_card(device.id, reused_record, original_card_number=card_number, **{**controller_fields, "is_valid": False})
            except AccessCardSDKError:
                pass
        enrollment_service.confirmation_failed_for_user(session_token)
        if isinstance(exc, IntegrityError):
            raise HTTPException(status_code=409, detail="The card was written but the application could not save the assignment; controller cleanup was attempted. Verify device inventory.") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        if "record_number" in locals():
            try:
                access_cards.delete_device_card(device.id, record_number)
            except AccessCardSDKError:
                pass
        if "reused_record" in locals():
            try:
                access_cards.update_device_card(device.id, reused_record, original_card_number=card_number, **{**controller_fields, "is_valid": False})
            except AccessCardSDKError:
                pass
        enrollment_service.confirmation_failed_for_user(session_token)
        raise


@router.get("/stations/{station_id}/users/{user_id}/card-history", response_model=list[UserCardAssignmentRead])
def list_station_user_card_history(station_id: int, user_id: int, db: Session = Depends(get_db)):
    _user_or_404(db, station_id, user_id)
    rows = db.query(UserCardAssignment).filter(
        UserCardAssignment.station_user_id == user_id,
        UserCardAssignment.station_id == station_id,
    ).order_by(UserCardAssignment.assigned_at.desc(), UserCardAssignment.id.desc()).all()
    return [_card_assignment_read(row) for row in rows]


@router.delete("/stations/{station_id}/users/{user_id}/card")
def deactivate_station_user_card(station_id: int, user_id: int, db: Session = Depends(get_db)):
    user = _user_or_404(db, station_id, user_id)
    link = _active_user_assignment(db, user.id)
    if link is None:
        raise HTTPException(status_code=404, detail="User has no active RFID card")
    card = db.get(StationCardAssignment, link.station_card_assignment_id)
    if card is None:
        raise HTTPException(status_code=409, detail="Card assignment record is missing; manual reconciliation is required")
    if card.device_record_no is None:
        raise HTTPException(status_code=409, detail="Controller record number is unknown. Reconcile the controller before revoking this card")
    device = _device_for_station(db, station_id, card.device_id)
    _ensure_connected(device, db)
    try:
        actual_record = access_cards.update_device_card(
            device.id,
            int(card.device_record_no),
            original_card_number=card.card_number,
            card_number=card.card_number,
            card_name=card.card_name,
            card_type=card.card_type,
            is_valid=False,
            valid_from=card.valid_from,
            valid_until=card.valid_until,
            door_indices=card.door_indices or [0],
            time_section_indices=card.time_section_indices or [0],
        )
    except AccessCardSDKError as exc:
        card.sync_status = "failed"
        card.last_sync_error = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Could not revoke the card on the Dahua controller: {exc}") from exc
    now = datetime.now(UTC)
    if actual_record is not None:
        card.device_record_no = actual_record  # repairs a stored number that pointed at the wrong record
    card.is_active = False
    card.is_valid = False
    card.device_card_status = 4
    card.sync_status = "pending_verification"
    card.last_sync_error = "Card revocation was sent; verify controller inventory."
    link.is_active = False
    link.ended_at = now
    db.commit()
    return {"deactivated": True, "station_user_id": user.id, "card_number": card.card_number, "sync_status": card.sync_status}


@router.post("/stations/{station_id}/users/{user_id}/cards/{assignment_id}/activate")
def activate_station_user_card(
    station_id: int,
    user_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    """Reactivate a previously assigned card without creating a new card record.

    A new UserCardAssignment history row is created; the old inactive link is
    retained with its original ended_at timestamp. The controller card itself
    is updated in place and must be inventory-verified afterwards.
    """
    user = _user_or_404(db, station_id, user_id)
    if not user.is_active:
        raise HTTPException(status_code=409, detail="Cannot reactivate a card for an inactive station user")
    _ensure_no_active_user_card(db, user)

    card = db.query(StationCardAssignment).filter(
        StationCardAssignment.id == assignment_id,
        StationCardAssignment.station_id == station_id,
    ).first()
    if card is None:
        raise HTTPException(status_code=404, detail="Station card assignment not found")
    if card.is_active:
        raise HTTPException(status_code=409, detail="This station card assignment is already active")

    previous_link = db.query(UserCardAssignment).filter(
        UserCardAssignment.station_user_id == user_id,
        UserCardAssignment.station_card_assignment_id == card.id,
        UserCardAssignment.station_id == station_id,
    ).order_by(UserCardAssignment.id.desc()).first()
    if previous_link is None:
        raise HTTPException(
            status_code=409,
            detail="This card was not previously assigned to this station user. Use the card-adoption workflow for a different owner.",
        )
    if previous_link.is_active:
        raise HTTPException(status_code=409, detail="This card already has an active assignment link")

    _ensure_card_not_assigned(db, card.card_number)
    if card.device_record_no is None:
        raise HTTPException(status_code=409, detail="Controller record number is unknown. Reconcile the controller before reactivating this card")

    device = _device_for_station(db, station_id, card.device_id)
    _ensure_connected(device, db)

    # Retain the original validity window. Do not silently extend an expired
    # card or change its door/time permissions as part of reactivation.
    today = datetime.now(PKT).date()
    valid_from = card.valid_from or today
    valid_until = card.valid_until or date(2037, 12, 31)
    if valid_from > today or valid_until < today:
        raise HTTPException(
            status_code=409,
            detail="The card's current validity dates do not include today. Update its validity dates before reactivating it.",
        )

    card_name = card.card_name or card.card_number
    link = UserCardAssignment(
        station_user_id=user.id,
        station_card_assignment_id=card.id,
        station_id=station_id,
        device_id=device.id,
        card_number=card.card_number,
        is_active=True,
    )

    # Flush first so database uniqueness rules are checked before enabling the
    # physical card. The transaction remains uncommitted until the SDK write
    # succeeds.
    card.is_active = True
    card.is_valid = True
    card.device_card_status = 0
    card.sync_status = "pending_verification"
    card.last_sync_error = "Card reactivation was sent; run controller inventory verification."
    card.valid_from = valid_from
    card.valid_until = valid_until
    card.card_name = card_name
    device.inventory_status = "verification_required"
    device.last_inventory_at = None
    device.observed_card_count = None
    db.add(link)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This user or RFID card already has an active card assignment") from exc

    try:
        actual_record = access_cards.update_device_card(
            device.id,
            int(card.device_record_no),
            original_card_number=card.card_number,
            card_number=card.card_number,
            card_name=card_name,
            card_type=card.card_type,
            is_valid=True,
            valid_from=valid_from,
            valid_until=valid_until,
            door_indices=card.door_indices or [0],
            time_section_indices=card.time_section_indices or [0],
        )
    except AccessCardSDKError as exc:
        db.rollback()
        failed_card = db.get(StationCardAssignment, assignment_id)
        if failed_card is not None:
            failed_card.sync_status = "failed"
            failed_card.last_sync_error = str(exc)
            db.commit()
        raise HTTPException(status_code=502, detail=f"Could not reactivate the card on the Dahua controller: {exc}") from exc

    card.last_synced_at = datetime.now(UTC)
    if actual_record is not None:
        card.device_record_no = actual_record
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Best-effort rollback of the hardware write if the database commit
        # unexpectedly fails after the controller accepted the update.
        try:
            access_cards.update_device_card(
                device.id, int(card.device_record_no),
                original_card_number=card.card_number, card_number=card.card_number,
                card_name=card_name, card_type=card.card_type, is_valid=False,
                valid_from=valid_from, valid_until=valid_until,
                door_indices=card.door_indices or [0],
                time_section_indices=card.time_section_indices or [0],
            )
        except AccessCardSDKError:
            pass
        raise HTTPException(status_code=409, detail="The card was updated on the controller but the database assignment could not be committed. Run inventory verification and reconcile before retrying.") from exc

    db.refresh(link)
    return {
        "reactivated": True,
        "station_user_id": user.id,
        "station_user_name": user.name,
        "station_card_assignment_id": card.id,
        "card_number": card.card_number,
        "is_valid": True,
        "sync_status": card.sync_status,
        "assignment": _card_assignment_read(link),
        "message": "The existing RFID card was reactivated on the Dahua controller. Run inventory verification before treating synchronization as complete.",
    }
