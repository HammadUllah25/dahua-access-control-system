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
from app.schemas.access_card import AccessCardCreate, AccessCardUpdate, AccessCardRead, DeviceCardRecordRead
from app.services.access_cards import access_cards, AccessCardSDKError
from app.services.device_sessions import sessions
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError

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


def _ensure_connected(device: Device, db: Session) -> None:
    try:
        if not sessions.is_connected(device.id):
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


@router.post("/devices/{device_id}/cards", response_model=AccessCardRead, status_code=status.HTTP_201_CREATED)
def assign_ic_card(device_id: int, payload: AccessCardCreate, db: Session = Depends(get_db)):
    device = _device_or_404(db, device_id)
    person = _person_or_404(db, payload.person_id)
    card_number = payload.card_number.upper()
    duplicate = db.query(AccessCard).filter(
        AccessCard.device_id == device_id,
        AccessCard.card_number == card_number,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This IC card is already assigned to this device in the application.")

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
        raise HTTPException(status_code=502, detail=str(exc)) from exc

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
        # The controller insert already succeeded. Attempt compensation so a
        # duplicate/racing DB write does not leave an untracked device card.
        try:
            access_cards.delete_device_card(device_id, record_no)
        except AccessCardSDKError:
            pass
        raise HTTPException(
            status_code=409,
            detail="The card was written to the controller, but the application could not save its assignment. A cleanup was attempted; read controller card records to verify.",
        ) from exc
    db.refresh(assignment)
    return assignment


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
    return rows




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
