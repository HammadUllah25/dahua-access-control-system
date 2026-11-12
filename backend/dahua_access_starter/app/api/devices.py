from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError
from app.services.device_sessions import sessions
from app.services.device_monitor import monitor
from app.services.realtime import (
    device_status_data,
    publish_device_deleted,
    publish_device_status,
)
from app.services.secret_store import encrypt_secret


router = APIRouter(prefix="/devices", tags=["Devices"])


def _get_device(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    return device


def _normalize_serial(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip().upper()
    return value or None


def _normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip().upper()
    return value or None


def _check_duplicate_identity(
    db: Session,
    serial_number: str | None,
    mac_address: str | None,
    exclude_device_id: int | None = None,
) -> None:
    """
    Prevent registering the same physical controller more than once.

    Serial numbers and MAC addresses are checked globally.
    Host/IP is intentionally not globally unique because
    different sites can reuse private IP addresses.
    """

    if serial_number:
        query = db.query(Device).filter(
            func.upper(Device.serial_number) == serial_number
        )

        if exclude_device_id is not None:
            query = query.filter(Device.id != exclude_device_id)

        if query.first():
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Device serial number '{serial_number}' "
                    "is already registered."
                )
            )

    if mac_address:
        query = db.query(Device).filter(
            func.upper(Device.mac_address) == mac_address
        )

        if exclude_device_id is not None:
            query = query.filter(Device.id != exclude_device_id)

        if query.first():
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Device MAC address '{mac_address}' "
                    "is already registered."
                )
            )


def _handle_identity_integrity_error(
    db: Session,
) -> None:
    """
    Database-level protection against simultaneous duplicate requests.
    """

    db.rollback()

    raise HTTPException(
        status_code=409,
        detail=(
            "A device with this serial number or MAC address "
            "is already registered."
        )
    )


@router.get("", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).order_by(Device.id.asc()).all()


@router.get("/status", tags=["Monitoring"])
def list_device_statuses(db: Session = Depends(get_db)):
    """Compact, credential-free status snapshot for dashboard initialization."""
    devices = db.query(Device).order_by(Device.id.asc()).all()
    items = [device_status_data(device) for device in devices]
    summary = {"total": len(items), "online": 0, "offline": 0, "pending": 0, "unknown": 0}
    for item in items:
        key = item["status"] if item["status"] in {"online", "offline", "pending"} else "unknown"
        summary[key] += 1
    return {"items": items, "summary": summary}



@router.post(
    "",
    response_model=DeviceRead,
    status_code=status.HTTP_201_CREATED
)
def add_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db)
):
    serial_number = _normalize_serial(payload.serial_number)
    mac_address = _normalize_mac(payload.mac_address)

    # Application-level duplicate checks.
    _check_duplicate_identity(
        db=db,
        serial_number=serial_number,
        mac_address=mac_address,
    )

    device = Device(
        name=payload.name.strip(),
        connection_type=payload.connection_type,
        host=payload.host.strip(),
        port=payload.port,
        username=payload.username.strip(),
        password_encrypted=encrypt_secret(payload.password),
        model=payload.model,
        serial_number=serial_number,
        mac_address=mac_address,
        status="pending",
        monitoring_enabled=payload.monitoring_enabled,
    )

    db.add(device)

    try:
        db.commit()
        db.refresh(device)

    except IntegrityError:
        _handle_identity_integrity_error(db)

    if payload.connect_now:
        device.last_connect_attempt_at = datetime.now(timezone.utc)

        try:
            session = sessions.connect(device)

            device.status = "online"
            device.serial_number = (
                session.serial_number or device.serial_number
            )
            device.last_connected_at = session.connected_at
            device.last_error = None

        except (
            SDKUnavailableError,
            DeviceLoginError,
            ValueError
        ) as exc:
            device.status = "offline"
            device.last_error = str(exc)

        db.commit()
        db.refresh(device)
        if device.status != "pending":
            publish_device_status(device, reason="device_registered_and_connected")

    return device


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    return _get_device(db, device_id)


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db)
):
    device = _get_device(db, device_id)
    previous_status = device.status

    values = payload.model_dump(
        exclude_unset=True,
        exclude={"password", "reconnect"}
    )

    # Normalize identity fields when they are supplied.
    if "serial_number" in values:
        values["serial_number"] = _normalize_serial(
            values["serial_number"]
        )

    if "mac_address" in values:
        values["mac_address"] = _normalize_mac(
            values["mac_address"]
        )

    candidate_serial = values.get(
        "serial_number",
        device.serial_number
    )

    candidate_mac = values.get(
        "mac_address",
        device.mac_address
    )

    # Don't allow changing a device's identity to another
    # already-registered controller's identity.
    _check_duplicate_identity(
        db=db,
        serial_number=candidate_serial,
        mac_address=candidate_mac,
        exclude_device_id=device.id,
    )

    changed_connection = any(
        getattr(payload, key) is not None
        for key in ("host", "port", "username", "password")
    )

    if changed_connection:
        sessions.disconnect(device.id)

    for key, value in values.items():
        # Explicit null can clear optional identity fields.
        if key in ("serial_number", "mac_address"):
            setattr(device, key, value)

        elif value is not None:
            setattr(
                device,
                key,
                value.strip() if isinstance(value, str) else value
            )

    if payload.password:
        device.password_encrypted = encrypt_secret(payload.password)

    if payload.monitoring_enabled is not None:
        device.monitoring_enabled = payload.monitoring_enabled

        if not payload.monitoring_enabled:
            sessions.disconnect(device.id)
            device.status = "offline"

    if changed_connection:
        device.status = (
            "pending" if device.monitoring_enabled else "offline"
        )
        device.last_error = None

    try:
        db.commit()
        db.refresh(device)

    except IntegrityError:
        _handle_identity_integrity_error(db)

    should_connect = (
        changed_connection or payload.reconnect
    ) and device.monitoring_enabled

    if should_connect:
        device.last_connect_attempt_at = datetime.now(timezone.utc)

        try:
            session = sessions.connect(device)

            device.status = "online"
            device.serial_number = (
                session.serial_number or device.serial_number
            )
            device.last_connected_at = session.connected_at
            device.last_error = None

        except (
            SDKUnavailableError,
            DeviceLoginError,
            ValueError
        ) as exc:
            device.status = "offline"
            device.last_error = str(exc)

        db.commit()
        db.refresh(device)

    if device.status != previous_status:
        publish_device_status(device, reason="device_updated")
    return device


@router.post("/{device_id}/connect", response_model=DeviceRead)
def connect_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    device = _get_device(db, device_id)
    previous_status = device.status

    device.monitoring_enabled = True
    device.last_connect_attempt_at = datetime.now(timezone.utc)

    try:
        session = sessions.connect(device)

        device.status = "online"
        device.serial_number = (
            session.serial_number or device.serial_number
        )
        device.last_connected_at = session.connected_at
        device.last_error = None

    except (
        SDKUnavailableError,
        DeviceLoginError,
        ValueError
    ) as exc:
        device.status = "offline"
        device.last_error = str(exc)

    db.commit()
    db.refresh(device)

    if device.status != previous_status:
        publish_device_status(device, reason="manual_connect")
    return device


@router.post("/{device_id}/disconnect", response_model=DeviceRead)
def disconnect_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    device = _get_device(db, device_id)
    previous_status = device.status

    sessions.disconnect(device.id)

    device.monitoring_enabled = False
    device.status = "offline"

    db.commit()
    db.refresh(device)

    if device.status != previous_status:
        publish_device_status(device, reason="manual_disconnect")
    return device


@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    device = _get_device(db, device_id)

    sessions.disconnect(device.id)

    db.delete(device)
    db.commit()
    publish_device_deleted(device_id)

    return {
        "deleted": True,
        "device_id": device_id
    }


@router.post("/{device_id}/health-check")
def check_device_health(device_id: int):
    """Run an immediate TCP/session health check for one registered device."""

    result = monitor.check_device_now(device_id)

    if result.get("result") == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    return result


@router.get("/monitor/status", tags=["Monitoring"])
def monitor_status():
    return monitor.status()
