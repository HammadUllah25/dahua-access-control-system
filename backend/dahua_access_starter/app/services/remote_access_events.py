from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.device import Device
from app.models.station import Station

# Dahua's access callback does not contain the software operator/customer ID.
# We correlate by controller + door + a narrow receive-time window. Both the
# callback writer and software audit writer use this lock so their DB writes
# cannot race inside this process.
REMOTE_CALLBACK_MATCH_WINDOW_SECONDS = 5
_REMOTE_EVENT_CORRELATION_LOCK = threading.RLock()


def remote_event_correlation_lock() -> threading.RLock:
    """Shared process-local lock for callback/audit correlation transactions."""
    return _REMOTE_EVENT_CORRELATION_LOCK


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _callback_is_already_attached(event: AccessEvent) -> bool:
    payload = event.raw_payload or {}
    return bool(payload.get("controller_callback_matched"))


def _apply_controller_callback(
    software_event: AccessEvent,
    *,
    callback_payload: dict[str, Any],
    callback_received_at: datetime,
    pending_row_id: int | None = None,
) -> None:
    """Attach the native controller evidence to the software audit row.

    Identity/authorization fields (event_source, user_type, operator_id,
    reason, command_status) intentionally remain from the software audit row.
    The raw Dahua payload is retained in full under controller_callback.
    """
    software_event.alarm_type = _as_int(callback_payload.get("alarm_type")) or 0
    software_event.event_id = _as_int(callback_payload.get("event_id"))
    software_event.sequence = _as_int(callback_payload.get("sequence"))
    software_event.door_number = (
        _as_int(callback_payload.get("door_number"))
        if callback_payload.get("door_number") is not None
        else software_event.door_number
    )
    software_event.door_name = callback_payload.get("door_name")
    software_event.card_number = None

    raw_user_id = callback_payload.get("user_id")
    software_event.user_id = (
        None if str(raw_user_id or "").strip() in {"", "0"} else str(raw_user_id)
    )
    software_event.cardholder_name = callback_payload.get("cardholder_name")
    software_event.reader_id = callback_payload.get("reader_id")
    software_event.event_type_code = _as_int(callback_payload.get("event_type_code"))
    software_event.open_method = _as_int(callback_payload.get("open_method"))
    software_event.card_type = _as_int(callback_payload.get("card_type"))

    callback_result = str(
        callback_payload.get("access_result") or software_event.access_result or "unknown"
    ).lower()
    software_event.access_result = callback_result
    software_event.raw_status_code = _as_int(callback_payload.get("raw_status_code"))
    software_event.raw_em_status_code = _as_int(
        callback_payload.get("raw_em_status_code")
    )
    software_event.error_code = _as_int(callback_payload.get("error_code"))

    device_event_time = _parse_datetime(callback_payload.get("device_event_time"))
    if device_event_time is not None:
        # The model stores device-local stuTime as a timezone-naive datetime.
        software_event.device_event_time = device_event_time.replace(tzinfo=None)

    event_time_utc = _parse_datetime(callback_payload.get("event_time_utc"))
    if event_time_utc is not None:
        software_event.event_time_utc = _as_utc(event_time_utc)

    # This row remains the single logical software transaction. Keep the
    # controller's native payload as evidence instead of making a second row.
    merged_payload = dict(software_event.raw_payload or {})
    merged_payload["controller_callback"] = dict(callback_payload)
    merged_payload["controller_callback_received_at"] = _as_utc(
        callback_received_at
    ).isoformat()
    merged_payload["controller_callback_matched"] = True
    if pending_row_id is not None:
        merged_payload["controller_callback_merged_from_event_id"] = pending_row_id
    software_event.raw_payload = merged_payload
    software_event.is_billable = False
    software_event.physical_door_state_verified = False


def attach_controller_callback_to_software_event(
    db: Session,
    *,
    device_id: int,
    door_number: int | None,
    callback_payload: dict[str, Any],
    callback_received_at: datetime,
) -> AccessEvent | None:
    """Attach a callback to the closest recent unmatched software unlock row.

    Returns the matched software event, or None when no matching audit exists.
    Caller must hold remote_event_correlation_lock() and commit the session.
    """
    if door_number is None:
        return None

    callback_time = _as_utc(callback_received_at)
    window = timedelta(seconds=REMOTE_CALLBACK_MATCH_WINDOW_SECONDS)
    candidates = (
        db.query(AccessEvent)
        .filter(
            AccessEvent.device_id == device_id,
            AccessEvent.door_number == door_number,
            AccessEvent.event_source == "REMOTE",
            AccessEvent.event_type == "REMOTE_UNLOCK",
            AccessEvent.command_status == "command_accepted",
            AccessEvent.received_at >= callback_time - window,
            AccessEvent.received_at <= callback_time + window,
        )
        .order_by(AccessEvent.received_at.desc(), AccessEvent.id.desc())
        .limit(20)
        .all()
    )

    eligible = [event for event in candidates if not _callback_is_already_attached(event)]
    if not eligible:
        return None

    matched = min(
        eligible,
        key=lambda event: abs(
            (_as_utc(event.received_at) - callback_time).total_seconds()
        ),
    )
    _apply_controller_callback(
        matched,
        callback_payload=callback_payload,
        callback_received_at=callback_time,
    )
    return matched


def _attach_pending_device_callback(
    db: Session,
    *,
    software_event: AccessEvent,
    issued_at: datetime,
) -> bool:
    """Handle the race where the Dahua callback is persisted before the audit.

    A matching temporary DEVICE row is merged into the new REMOTE software row
    and deleted. Its complete native callback is preserved in raw_payload.
    Caller must hold remote_event_correlation_lock().
    """
    if software_event.device_id is None or software_event.door_number is None:
        return False

    issued_time = _as_utc(issued_at)
    window = timedelta(seconds=REMOTE_CALLBACK_MATCH_WINDOW_SECONDS)
    candidates = (
        db.query(AccessEvent)
        .filter(
            AccessEvent.device_id == software_event.device_id,
            AccessEvent.door_number == software_event.door_number,
            AccessEvent.event_source == "DEVICE",
            AccessEvent.event_type == "REMOTE_UNLOCK",
            AccessEvent.received_at >= issued_time - window,
            AccessEvent.received_at <= issued_time + window,
        )
        .order_by(AccessEvent.received_at.desc(), AccessEvent.id.desc())
        .limit(20)
        .all()
    )

    if not candidates:
        return False

    pending = min(
        candidates,
        key=lambda event: abs(
            (_as_utc(event.received_at) - issued_time).total_seconds()
        ),
    )
    pending_payload = dict(pending.raw_payload or {})
    _apply_controller_callback(
        software_event,
        callback_payload=pending_payload,
        callback_received_at=pending.received_at,
        pending_row_id=pending.id,
    )
    db.delete(pending)
    return True


def record_remote_unlock_event(
    db: Session,
    *,
    device: Device,
    door_index: int,
    user_type: str,
    operator_id: str | None,
    reason: str,
    command_status: str,
    payment_reference: str | None = None,
    sdk_result: int | None = None,
    error: str | None = None,
) -> AccessEvent:
    """Persist one software unlock transaction and merge any nearby callback."""
    with remote_event_correlation_lock():
        station = db.get(Station, device.station_id) if device.station_id else None
        now = datetime.now(timezone.utc)
        accepted = command_status == "command_accepted"
        payload: dict[str, Any] = {
            "source": "SOFTWARE",
            "event_type": "REMOTE_UNLOCK",
            "door_index": door_index,
            "operator_id": operator_id,
            "reason": reason,
            "command_status": command_status,
            "sdk_result": sdk_result,
            "physical_door_state_verified": False,
        }
        if error:
            payload["error"] = error[:500]

        event = AccessEvent(
            device_id=device.id,
            device_name=device.name,
            device_host=device.host,
            device_serial_number=device.serial_number,
            station_id=station.id if station else device.station_id,
            station_name=station.name if station else None,
            card_role=None,
            station_user_id=None,
            station_user_name=None,
            is_billable=False,
            currency="PKR",
            source_event_key=None,
            event_source="REMOTE",
            event_type="REMOTE_UNLOCK",
            user_type=user_type,
            operator_id=operator_id,
            reason=reason,
            payment_reference=payment_reference,
            command_status=command_status,
            physical_door_state_verified=False,
            alarm_type=0,
            event_id=None,
            sequence=None,
            door_number=door_index,
            door_name=None,
            card_number=None,
            user_id=None,
            cardholder_name=None,
            reader_id=None,
            event_direction="REMOTE",
            event_type_code=None,
            open_method=None,
            card_type=None,
            access_result="granted" if accepted else "denied",
            raw_status_code=1 if accepted else 0,
            raw_em_status_code=None,
            error_code=None,
            device_event_time=None,
            event_time_utc=now,
            received_at=now,
            raw_payload=payload,
        )

        db.add(event)
        db.flush()

        # If the native callback won the race and was stored first, fold it
        # into this software event and remove only that duplicate callback row.
        if accepted:
            _attach_pending_device_callback(
                db,
                software_event=event,
                issued_at=now,
            )

        db.commit()
        db.refresh(event)
        return event
