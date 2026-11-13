from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.device import Device
from app.models.person import Person
from app.models.access_card import AccessCard
from app.schemas.person import PersonCreate, PersonUpdate, PersonRead
from app.schemas.access_card import (
    AccessCardCreate, AccessCardUpdate, AccessCardRead,
    DeviceCardRecordRead, DevicePersonProfileRead,
)
from app.schemas.card_enrollment import (
    CardEnrollmentStart, CardEnrollmentRead, CardEnrollmentConfirm,
    CardEnrollmentConfirmRead,
)
from app.services.card_enrollment import (
    enrollment_service, CardEnrollmentError,
)
from app.services.access_cards import access_cards, AccessCardSDKError
from app.services.device_sessions import sessions
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError
from app.services.realtime import publish_device_status

router = APIRouter(tags=["People and IC Cards"])


def _person_or_404(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


def _device_or_404(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _uses_asi1201e_card_record_workflow(device: Device) -> bool:
    """Return True for ASI1201E-family models handled as card-record devices here."""
    return "ASI1201E" in (device.model or "").upper()


def _ensure_connected(device: Device, db: Session) -> None:
    previous_status = device.status
    try:
        if not sessions.is_connected(device.id):
            session = sessions.connect(device)
            device.status = "online"
            device.serial_number = session.serial_number or device.serial_number
            device.last_connected_at = session.connected_at
            device.last_error = None
            db.commit()
            if device.status != previous_status:
                publish_device_status(device, reason="card_operation_connected")
    except (SDKUnavailableError, DeviceLoginError, ValueError) as exc:
        device.status = "offline"
        device.last_error = str(exc)
        db.commit()
        if device.status != previous_status:
            publish_device_status(device, reason="card_operation_connection_failed")
        raise HTTPException(status_code=503, detail=f"Could not connect to Dahua device: {exc}") from exc


@router.post("/persons", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)):
    existing = db.query(Person).filter(Person.person_code == payload.person_code.strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="person_code already exists")
    person = Person(
        person_code=payload.person_code.strip(),
        name=payload.name.strip(),
        department=payload.department.strip() if payload.department else None,
        phone=payload.phone.strip() if payload.phone else None,
        email=payload.email.strip().lower() if payload.email else None,
        profile_source="application",
        source_device_id=None,
    )
    db.add(person)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="person_code already exists") from exc
    db.refresh(person)
    return person


@router.get("/persons", response_model=list[PersonRead])
def list_persons(db: Session = Depends(get_db)):
    return db.query(Person).order_by(Person.id.asc()).all()


@router.get("/persons/{person_id}", response_model=PersonRead)
def get_person(person_id: int, db: Session = Depends(get_db)):
    return _person_or_404(db, person_id)


@router.put("/persons/{person_id}", response_model=PersonRead)
def update_person(person_id: int, payload: PersonUpdate, db: Session = Depends(get_db)):
    person = _person_or_404(db, person_id)
    values = payload.model_dump(exclude_unset=True)
    if "person_code" in values and values["person_code"]:
        duplicate = db.query(Person).filter(Person.person_code == values["person_code"].strip(), Person.id != person_id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="person_code already exists")
    for key, value in values.items():
        if value is None and key in ("person_code", "name"):
            continue
        if isinstance(value, str):
            value = value.strip()
            if key == "email" and value:
                value = value.lower()
            if value == "":
                value = None if key != "name" and key != "person_code" else value
        setattr(person, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="person_code already exists") from exc
    db.refresh(person)
    return person


@router.get("/persons/{person_id}/cards", response_model=list[AccessCardRead])
def list_person_cards(person_id: int, db: Session = Depends(get_db)):
    _person_or_404(db, person_id)
    return (
        db.query(AccessCard)
        .filter(AccessCard.person_id == person_id)
        .order_by(AccessCard.device_id.asc(), AccessCard.id.asc())
        .all()
    )


@router.delete("/persons/{person_id}")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = _person_or_404(db, person_id)
    assignments = db.query(AccessCard).filter(AccessCard.person_id == person_id).count()
    if assignments:
        raise HTTPException(
            status_code=409,
            detail=f"Person has {assignments} assigned IC card(s). Delete/revoke those device card assignments first.",
        )
    db.delete(person)
    db.commit()
    return {"deleted": True, "person_id": person_id}


def _write_card_assignment(
    device_id: int,
    payload: AccessCardCreate,
    db: Session,
) -> AccessCard:
    device = _device_or_404(db, device_id)
    person = _person_or_404(db, payload.person_id)
    card_number = payload.card_number.upper()
    duplicate = db.query(AccessCard).filter(
        AccessCard.device_id == device_id,
        AccessCard.card_number == card_number,
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="This IC card is already assigned to this device in the application.",
        )

    _ensure_connected(device, db)
    card_name = (payload.card_name or person.name).strip()
    card_type_map = {"general": 0, "vip": 1, "guest": 2}
    try:
        record_no = access_cards.add_device_card(
            device_id,
            card_number=card_number,
            card_name=card_name,
            card_type=card_type_map[payload.card_type],
            is_valid=payload.is_valid,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            door_indices=payload.door_indices,
            time_section_indices=payload.time_section_indices,
        )
    except AccessCardSDKError as exc:
        message = str(exc)
        code = 409 if "already exists" in message.lower() else 502
        raise HTTPException(status_code=code, detail=message) from exc

    assignment = AccessCard(
        person_id=person.id,
        device_id=device_id,
        card_number=card_number,
        card_name=card_name,
        device_record_no=record_no,
        card_type=card_type_map[payload.card_type],
        device_card_status=0,
        is_valid=payload.is_valid,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        door_indices=payload.door_indices,
        time_section_indices=payload.time_section_indices,
        sync_status="synced",
        last_sync_error=None,
        last_synced_at=datetime.now(timezone.utc),
    )
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        try:
            access_cards.delete_device_card(device_id, record_no)
        except AccessCardSDKError:
            pass
        raise HTTPException(
            status_code=409,
            detail=(
                "The card was written to the controller, but the application could not save its assignment. "
                "A cleanup was attempted; read controller card records to verify."
            ),
        ) from exc
    db.refresh(assignment)
    return assignment


@router.post("/devices/{device_id}/cards", response_model=AccessCardRead, status_code=status.HTTP_201_CREATED)
def assign_ic_card(device_id: int, payload: AccessCardCreate, db: Session = Depends(get_db)):
    return _write_card_assignment(device_id, payload, db)


@router.post(
    "/devices/{device_id}/card-enrollments",
    response_model=CardEnrollmentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def begin_card_enrollment(
    device_id: int,
    payload: CardEnrollmentStart,
    db: Session = Depends(get_db),
):
    """Start listening for one RFID scan; the card UID is captured from Dahua alarm events."""
    device = _device_or_404(db, device_id)
    _ensure_connected(device, db)
    session = sessions.get_session(device_id)
    if session is None or not session.alarm_listening:
        # A previous login may have remained online after its alarm subscription failed.
        if session is not None:
            sessions.disconnect(device_id)
        _ensure_connected(device, db)
        session = sessions.get_session(device_id)
    if session is None or not session.alarm_listening:
        reason = session.subscription_error if session else "No active SDK login."
        raise HTTPException(
            status_code=503,
            detail=(
                "The device is connected, but Dahua alarm listening is not active. "
                f"Subscription detail: {reason or 'unknown error'}"
            ),
        )
    try:
        result = enrollment_service.begin(device_id, payload.timeout_seconds)
    except CardEnrollmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.get(
    "/devices/{device_id}/card-enrollments/{session_token}",
    response_model=CardEnrollmentRead,
)
def get_card_enrollment(device_id: int, session_token: str):
    result = enrollment_service.get(device_id, session_token)
    if result is None:
        raise HTTPException(status_code=404, detail="Card enrollment session not found.")
    return result


@router.delete(
    "/devices/{device_id}/card-enrollments/{session_token}",
    response_model=CardEnrollmentRead,
)
def cancel_card_enrollment(device_id: int, session_token: str):
    try:
        result = enrollment_service.cancel(device_id, session_token)
    except CardEnrollmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Card enrollment session not found.")
    return result


@router.post(
    "/devices/{device_id}/card-enrollments/{session_token}/confirm",
    response_model=CardEnrollmentConfirmRead,
    status_code=status.HTTP_201_CREATED,
)
def confirm_card_enrollment(
    device_id: int,
    session_token: str,
    payload: CardEnrollmentConfirm,
    db: Session = Depends(get_db),
):
    """Write the captured IC card record and link it to the selected app person.

    The ASI1201E enrollment path uses the legacy card-record API implemented by
    ``_write_card_assignment``. The central Person record is authoritative for
    the person-to-card relationship; confirmation does not create a separate
    controller personnel profile through OperateAccessUserService.
    """
    person = _person_or_404(db, payload.person_id)
    try:
        enrollment = enrollment_service.claim_for_confirmation(device_id, session_token)
    except CardEnrollmentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        card_number = enrollment.card_number or ""
        # Reuse the same validation and legacy RECORDSET_INSERT path as the
        # ordinary POST /devices/{device_id}/cards endpoint. The UID comes only
        # from the captured enrollment event, never from the confirmation body.
        try:
            card_payload = AccessCardCreate(
                person_id=person.id,
                card_number=card_number,
                card_name=payload.card_name or person.name,
                card_type=payload.card_type,
                is_valid=payload.is_valid,
                valid_from=payload.valid_from,
                valid_until=payload.valid_until,
                door_indices=payload.door_indices,
                time_section_indices=payload.time_section_indices,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"The captured card UID is not a supported hexadecimal IC UID: {exc}",
            ) from exc

        assignment = _write_card_assignment(device_id, card_payload, db)
        enrollment_service.confirmation_succeeded(device_id, session_token)
        return {
            "message": "Captured card was registered on the Dahua controller and linked to the application person.",
            "person_id": person.id,
            "card": assignment,
        }
    except Exception:
        enrollment_service.confirmation_failed(device_id, session_token)
        raise


@router.get("/devices/{device_id}/cards", response_model=list[AccessCardRead])
def list_assigned_cards(device_id: int, db: Session = Depends(get_db)):
    _device_or_404(db, device_id)
    return (
        db.query(AccessCard)
        .options(joinedload(AccessCard.person))
        .filter(AccessCard.device_id == device_id)
        .order_by(AccessCard.id.asc())
        .all()
    )


@router.get("/devices/{device_id}/cards/device-records", response_model=list[DeviceCardRecordRead])
def list_controller_cards(device_id: int, db: Session = Depends(get_db)):
    device = _device_or_404(db, device_id)
    _ensure_connected(device, db)
    try:
        rows = access_cards.list_device_cards(device_id)
    except AccessCardSDKError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # A card row and a person profile are separate records in Dahua NetSDK.
    # Link them through szUserID when the controller supplies it. Keep the card
    # result available even when the firmware does not implement person lookup.
    # The ASI1201E card workflow keeps the person link in the application DB;
    # do not invoke its separately failing/optional personnel-service GET API.
    uses_legacy_workflow = _uses_asi1201e_card_record_workflow(device)
    if uses_legacy_workflow:
        # Do not surface the legacy record's unlinked szUserID bytes as a person
        # identity; the authoritative link is the application's AccessCard row.
        for row in rows:
            row["device_user_id"] = None
    user_ids = [] if uses_legacy_workflow else list(dict.fromkeys(
        row.get("device_user_id") for row in rows if row.get("device_user_id")
    ))
    profiles: dict[str, dict] = {}
    lookup_error: str | None = None
    if user_ids:
        try:
            profiles = access_cards.get_device_user_records(device_id, user_ids)
        except AccessCardSDKError as exc:
            lookup_error = str(exc)

    for row in rows:
        user_id = row.get("device_user_id")
        row["person_profile"] = profiles.get(user_id) if user_id else None
        row["person_profile_error"] = (
            lookup_error if lookup_error else
            (f"No person record returned for device user ID {user_id}."
             if user_id and user_id not in profiles else None)
        )
    return rows




@router.get(
    "/devices/{device_id}/person-records/{device_user_id}",
    response_model=DevicePersonProfileRead,
    responses={501: {"description": "Separate personnel lookup is not enabled for ASI1201E card-record devices."}},
)
def get_controller_person_record(
    device_id: int, device_user_id: str, db: Session = Depends(get_db)
):
    """Read one native Dahua person record by its controller-side user ID."""
    device = _device_or_404(db, device_id)
    if _uses_asi1201e_card_record_workflow(device):
        raise HTTPException(
            status_code=501,
            detail=(
                "Separate Dahua personnel-profile lookup is not enabled for the ASI1201E card-record workflow. "
                "Use GET /persons and GET /devices/{device_id}/cards for application personnel/card assignments."
            ),
        )
    _ensure_connected(device, db)
    try:
        row = access_cards.get_device_user_record(device_id, device_user_id)
    except AccessCardSDKError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dahua returned no person record for device user ID {device_user_id!r}.",
        )
    return row


@router.post("/devices/{device_id}/cards/import", tags=["People and IC Cards"])
def import_controller_cards(device_id: int, db: Session = Depends(get_db)):
    """Import card records already enrolled on the physical controller.

    Existing app assignments are reconciled by (device_id, card_number). New
    controller-only cards create a minimal placeholder Person so GET /persons
    can display them. We deliberately do not match by name: names are not unique,
    and the ASI1201E legacy card structure documents szUserID as unsupported.
    """
    device = _device_or_404(db, device_id)
    _ensure_connected(device, db)

    try:
        device_rows = access_cards.list_device_cards(device_id)
    except AccessCardSDKError as exc:
        raise HTTPException(status_code=502, detail=f"Could not read card records from controller: {exc}") from exc

    existing_rows = (
        db.query(AccessCard)
        .filter(AccessCard.device_id == device_id)
        .all()
    )
    assignment_by_card = {row.card_number.upper(): row for row in existing_rows}
    imported_people = 0
    imported_cards = 0
    updated_assignments = 0
    skipped_records: list[dict] = []
    imported_items: list[dict] = []
    now = datetime.now(timezone.utc)

    try:
        for row in device_rows:
            card_number = (row.get("card_number") or "").strip().upper()
            if not card_number:
                skipped_records.append({
                    "record_number": row.get("record_number"),
                    "reason": "Controller record has an empty card number.",
                })
                continue

            assignment = assignment_by_card.get(card_number)
            if assignment is not None:
                # Preserve the existing person link; refresh device-owned fields.
                assignment.device_record_no = int(row["record_number"])
                assignment.card_name = row.get("card_name") or assignment.card_name
                assignment.card_type = int(row.get("card_type", assignment.card_type))
                assignment.device_card_status = int(row.get("card_status", assignment.device_card_status))
                assignment.is_valid = bool(row.get("is_valid", assignment.is_valid))
                assignment.valid_from = row.get("valid_from")
                assignment.valid_until = row.get("valid_until")
                assignment.door_indices = list(row.get("door_indices") or [])
                assignment.time_section_indices = list(row.get("time_section_indices") or [])
                assignment.sync_status = "synced"
                assignment.last_sync_error = None
                assignment.last_synced_at = now
                updated_assignments += 1
                person = db.get(Person, assignment.person_id)
                imported_items.append({
                    "card_number": card_number,
                    "record_number": int(row["record_number"]),
                    "person_id": assignment.person_id,
                    "person_code": person.person_code if person else None,
                    "action": "updated_existing_assignment",
                })
                continue

            record_number = int(row.get("record_number") or 0)
            digest = sha256(f"{device_id}:{record_number}:{card_number}".encode("utf-8")).hexdigest()[:10]
            person_code = f"IMP-D{device_id}-R{record_number}-{digest}"
            person = db.query(Person).filter(Person.person_code == person_code).first()
            reused_by_card_uid = False
            created_placeholder = False
            if person is None:
                # A card UID can identify the same credential across multiple
                # controllers. Reuse a central person only when that UID maps to
                # exactly one person; never guess by matching display names.
                known_person_ids = {
                    int(item.person_id)
                    for item in db.query(AccessCard)
                    .filter(AccessCard.card_number == card_number)
                    .all()
                }
                if len(known_person_ids) == 1:
                    person = db.get(Person, next(iter(known_person_ids)))
                    reused_by_card_uid = person is not None
                elif len(known_person_ids) > 1:
                    skipped_records.append({
                        "record_number": record_number,
                        "card_number": card_number,
                        "reason": "This card UID is linked to multiple central people; manual resolution is required.",
                    })
                    continue
            if person is None:
                display_name = (row.get("card_name") or "").strip() or f"Imported card {card_number[-8:]}"
                person = Person(
                    person_code=person_code,
                    name=display_name[:120],
                    department=None,
                    phone=None,
                    email=None,
                    profile_source="device_import",
                    source_device_id=device_id,
                )
                db.add(person)
                db.flush()
                imported_people += 1
                created_placeholder = True

            assignment = AccessCard(
                person_id=person.id,
                device_id=device_id,
                card_number=card_number,
                card_name=(row.get("card_name") or person.name or f"Card {card_number[-8:]}")[:64],
                device_record_no=record_number,
                card_type=int(row.get("card_type", 0)),
                device_card_status=int(row.get("card_status", 0)),
                is_valid=bool(row.get("is_valid", False)),
                valid_from=row.get("valid_from"),
                valid_until=row.get("valid_until"),
                door_indices=list(row.get("door_indices") or []),
                time_section_indices=list(row.get("time_section_indices") or []),
                sync_status="synced",
                last_sync_error=None,
                last_synced_at=now,
            )
            db.add(assignment)
            db.flush()
            assignment_by_card[card_number] = assignment
            imported_cards += 1
            imported_items.append({
                "card_number": card_number,
                "record_number": record_number,
                "person_id": person.id,
                "person_code": person.person_code,
                "action": (
                    "imported_new_card_and_placeholder_person" if created_placeholder
                    else "imported_card_linked_to_existing_person" if reused_by_card_uid
                    else "linked_existing_placeholder_person"
                ),
            })

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "Import encountered a database uniqueness conflict. No import changes were committed. "
                "Refresh controller records and retry."
            ),
        ) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "device_id": device_id,
        "device_name": device.name,
        "device_serial_number": device.serial_number,
        "controller_records_found": len(device_rows),
        "new_people_created": imported_people,
        "new_card_assignments_created": imported_cards,
        "existing_assignments_refreshed": updated_assignments,
        "skipped_records": skipped_records,
        "items": imported_items,
        "note": (
            "Imported people are minimal profiles created from card records. "
            "Complete their employee codes, department, contact details, and identity "
            "in the central application. Existing person links are never matched by name."
        ),
    }


@router.put("/devices/{device_id}/cards/{assignment_id}", response_model=AccessCardRead)
def update_ic_card(device_id: int, assignment_id: int, payload: AccessCardUpdate, db: Session = Depends(get_db)):
    device = _device_or_404(db, device_id)
    assignment = db.query(AccessCard).filter(
        AccessCard.id == assignment_id,
        AccessCard.device_id == device_id,
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Card assignment not found for this device")
    updates = payload.model_dump(exclude_unset=True)
    new_number = (updates.get("card_number") or assignment.card_number).upper()
    collision = db.query(AccessCard).filter(
        AccessCard.device_id == device_id,
        AccessCard.card_number == new_number,
        AccessCard.id != assignment.id,
    ).first()
    if collision:
        raise HTTPException(status_code=409, detail="This card number is already assigned to this device")

    if assignment.device_record_no is None:
        raise HTTPException(status_code=409, detail="Device record number is missing; the card must be synchronized before it can be updated.")

    _ensure_connected(device, db)
    values = {
        "card_number": new_number,
        "card_name": updates.get("card_name") or assignment.card_name,
        "card_type": {"general": 0, "vip": 1, "guest": 2}.get(updates.get("card_type"), assignment.card_type),
        "is_valid": assignment.is_valid if updates.get("is_valid") is None else updates.get("is_valid"),
        "valid_from": updates.get("valid_from") or assignment.valid_from,
        "valid_until": updates.get("valid_until") or assignment.valid_until,
        "door_indices": updates.get("door_indices") or assignment.door_indices,
        "time_section_indices": updates.get("time_section_indices") or assignment.time_section_indices,
    }
    if values["valid_from"] and values["valid_until"] and values["valid_until"] < values["valid_from"]:
        raise HTTPException(status_code=422, detail="valid_until must be on or after valid_from")
    try:
        access_cards.update_device_card(
            device_id,
            int(assignment.device_record_no),
            original_card_number=assignment.card_number,
            **values,
        )
    except AccessCardSDKError as exc:
        assignment.sync_status = "failed"
        assignment.last_sync_error = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    for key, value in values.items():
        setattr(assignment, key, value)
    assignment.device_card_status = 0
    assignment.sync_status = "synced"
    assignment.last_sync_error = None
    assignment.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/devices/{device_id}/cards/{assignment_id}")
def delete_ic_card(device_id: int, assignment_id: int, db: Session = Depends(get_db)):
    device = _device_or_404(db, device_id)
    assignment = db.query(AccessCard).filter(
        AccessCard.id == assignment_id,
        AccessCard.device_id == device_id,
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Card assignment not found for this device")
    _ensure_connected(device, db)
    if assignment.device_record_no is None:
        raise HTTPException(status_code=409, detail="Device record number is missing; synchronize the card first")
    try:
        access_cards.delete_device_card(device_id, assignment.device_record_no)
    except AccessCardSDKError as exc:
        assignment.sync_status = "failed"
        assignment.last_sync_error = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    db.delete(assignment)
    db.commit()
    return {"deleted": True, "assignment_id": assignment_id, "device_id": device_id}
