from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError
from app.services.device_sessions import sessions
from app.services.device_monitor import monitor
from app.services.secret_store import encrypt_secret

router = APIRouter(prefix="/devices", tags=["Devices"])


def _get_device(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).order_by(Device.id.asc()).all()


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def add_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    device = Device(
        name=payload.name.strip(),
        connection_type=payload.connection_type,
        host=payload.host.strip(),
        port=payload.port,
        username=payload.username.strip(),
        password_encrypted=encrypt_secret(payload.password),
        model=payload.model or "ASI1201E",
        status="pending",
        monitoring_enabled=payload.monitoring_enabled,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    if payload.connect_now:
        device.last_connect_attempt_at = datetime.now(timezone.utc)
        try:
            session = sessions.connect(device)
            device.status = "online"
            device.serial_number = session.serial_number or device.serial_number
            device.last_connected_at = session.connected_at
            device.last_error = None
        except (SDKUnavailableError, DeviceLoginError, ValueError) as exc:
            device.status = "offline"
            device.last_error = str(exc)
        db.commit()
        db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)):
    return _get_device(db, device_id)


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)):
    device = _get_device(db, device_id)
    changed_connection = any(
        getattr(payload, key) is not None for key in ("host", "port", "username", "password")
    )
    if changed_connection:
        sessions.disconnect(device.id)

    values = payload.model_dump(exclude_unset=True, exclude={"password", "reconnect"})
    for key, value in values.items():
        if value is not None:
            setattr(device, key, value.strip() if isinstance(value, str) else value)
    if payload.password:
        device.password_encrypted = encrypt_secret(payload.password)
    if payload.monitoring_enabled is not None:
        device.monitoring_enabled = payload.monitoring_enabled
        if not payload.monitoring_enabled:
            sessions.disconnect(device.id)
            device.status = "offline"
    if changed_connection:
        device.status = "pending" if device.monitoring_enabled else "offline"
        device.last_error = None

    db.commit()
    db.refresh(device)

    should_connect = (changed_connection or payload.reconnect) and device.monitoring_enabled
    if should_connect:
        device.last_connect_attempt_at = datetime.now(timezone.utc)
        try:
            session = sessions.connect(device)
            device.status = "online"
            device.serial_number = session.serial_number or device.serial_number
            device.last_connected_at = session.connected_at
            device.last_error = None
        except (SDKUnavailableError, DeviceLoginError, ValueError) as exc:
            device.status = "offline"
            device.last_error = str(exc)
        db.commit()
        db.refresh(device)
    return device


@router.post("/{device_id}/connect", response_model=DeviceRead)
def connect_device(device_id: int, db: Session = Depends(get_db)):
    device = _get_device(db, device_id)
    device.monitoring_enabled = True
    device.last_connect_attempt_at = datetime.now(timezone.utc)
    try:
        session = sessions.connect(device)
        device.status = "online"
        device.serial_number = session.serial_number or device.serial_number
        device.last_connected_at = session.connected_at
        device.last_error = None
    except (SDKUnavailableError, DeviceLoginError, ValueError) as exc:
        device.status = "offline"
        device.last_error = str(exc)
    db.commit()
    db.refresh(device)
    return device


@router.post("/{device_id}/disconnect", response_model=DeviceRead)
def disconnect_device(device_id: int, db: Session = Depends(get_db)):
    device = _get_device(db, device_id)
    sessions.disconnect(device.id)
    device.monitoring_enabled = False
    device.status = "offline"
    db.commit()
    db.refresh(device)
    return device


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = _get_device(db, device_id)
    sessions.disconnect(device.id)
    db.delete(device)
    db.commit()
    return {"deleted": True, "device_id": device_id}


@router.post("/{device_id}/health-check")
def check_device_health(device_id: int):
    """Run an immediate TCP/session health check for one registered device."""
    result = monitor.check_device_now(device_id)
    if result.get("result") == "not_found":
        raise HTTPException(status_code=404, detail="Device not found")
    return result


@router.get("/monitor/status", tags=["Monitoring"])
def monitor_status():
    return monitor.status()
