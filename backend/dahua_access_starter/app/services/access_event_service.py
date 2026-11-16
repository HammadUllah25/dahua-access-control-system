from __future__ import annotations

import logging
import queue
import threading
from hashlib import sha256
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any

from app.core.database import SessionLocal
from app.models.access_event import AccessEvent
from app.models.device import Device
from app.models.station_card_assignment import StationCardAssignment
from app.models.station_rate import StationRate
from app.models.station import Station
from app.models.station_user import StationUser
from app.models.operational_role import OperationalRole
from app.models.user_card_assignment import UserCardAssignment

logger = logging.getLogger(__name__)
_STOP = object()
PKT = ZoneInfo("Asia/Karachi")
UTC = timezone.utc


class AccessEventService:
    """Persist native access events away from the NetSDK callback thread."""

    def __init__(self, max_queue_size: int = 10000) -> None:
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=max_queue_size)
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._running = False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._worker,
                name="dahua-access-event-writer",
                daemon=True,
            )
            self._thread.start()
            logger.info("Access event persistence worker started.")

    def enqueue(
        self,
        *,
        device_id: int,
        payload: dict[str, Any],
        device_name: str | None,
        device_host: str | None,
        device_serial_number: str | None,
    ) -> None:
        item = {
            "device_id": int(device_id),
            "payload": dict(payload),
            "device_name": device_name,
            "device_host": device_host,
            "device_serial_number": device_serial_number,
        }
        # Enrollment matching is an in-memory operation and must remain quick;
        # database writes are still handled by the separate worker below.
        try:
            from app.services.card_enrollment import enrollment_service
            if enrollment_service.observe_event(int(device_id), item["payload"]):
                logger.info(
                    "Card UID captured for enrollment | device_id=%s | card=%s",
                    device_id,
                    item["payload"].get("card_number"),
                )
        except Exception:
            logger.exception("Could not match Dahua event to an active card enrollment.")
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            logger.error(
                "Access event queue is full; event was not persisted | device_id=%s | event_id=%s",
                device_id,
                payload.get("event_id"),
            )

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is _STOP:
                    return
                self._persist(item)
            except Exception:
                logger.exception("Failed to persist a Dahua access event.")
            finally:
                self._queue.task_done()

    def _persist(self, item: dict[str, Any]) -> None:
        payload = item["payload"]
        db = SessionLocal()
        try:
            device = db.get(Device, item["device_id"])
            # If a controller is deleted after the callback, preserve the event and its snapshots.
            device_id = device.id if device is not None else None
            card_number = str(payload.get("card_number") or "").strip().upper() or None
            station = db.get(Station, device.station_id) if device and device.station_id else None
            assignment = None
            user_assignment = None
            station_user = None
            operational_role = None
            if device_id is not None and card_number:
                assignment = db.query(StationCardAssignment).filter(
                    StationCardAssignment.device_id == device_id,
                    StationCardAssignment.card_number == card_number,
                ).first()
                if assignment is not None and assignment.is_active:
                    user_assignment = db.query(UserCardAssignment).filter(
                        UserCardAssignment.station_card_assignment_id == assignment.id,
                        UserCardAssignment.is_active.is_(True),
                    ).first()
                    if user_assignment is not None:
                        station_user = db.get(StationUser, user_assignment.station_user_id)
                        if station_user is not None:
                            operational_role = db.get(OperationalRole, station_user.role_id)
            access_result = str(payload.get("access_result") or "unknown").lower()
            direction = str(payload.get("event_direction") or "UNKNOWN").upper()
            is_granted_entry = access_result == "granted" and direction == "ENTRY"
            if station_user is not None and operational_role is not None:
                role_code = operational_role.code
                effective_billable = (
                    station_user.is_billable_override
                    if station_user.is_billable_override is not None
                    else operational_role.default_is_billable
                )
                user_is_eligible = station_user.is_active
            else:
                # Legacy station cards remain supported during migration.
                role_code = assignment.role if assignment is not None else None
                effective_billable = bool(assignment and assignment.is_billable and assignment.role == "USER")
                user_is_eligible = True
            is_billable = bool(
                assignment is not None
                and assignment.is_active
                and assignment.is_valid
                and effective_billable
                and user_is_eligible
                and station is not None
                and station.is_active
                and is_granted_entry
            )
            received_at = datetime.now(UTC)
            event_timestamp = _parse_datetime(payload.get("event_time_utc")) or received_at
            if event_timestamp.tzinfo is None:
                event_timestamp = event_timestamp.replace(tzinfo=UTC)
            local_event_day = event_timestamp.astimezone(PKT).date()
            applied_rate = None
            currency = "PKR"
            if is_billable and station is not None and assignment is not None:
                rate = db.query(StationRate).filter(
                    StationRate.station_id == station.id,
                    # Current rate configuration keeps the legacy USER/STAFF price buckets.
                    # New role-specific pricing can be introduced separately without
                    # changing the operational-role assignment model.
                    StationRate.role == ("USER" if is_billable else "STAFF"),
                    StationRate.effective_from <= local_event_day,
                    (StationRate.effective_until.is_(None) | (StationRate.effective_until >= local_event_day)),
                ).order_by(StationRate.effective_from.desc(), StationRate.id.desc()).first()
                if rate is not None:
                    applied_rate = rate.rate_per_use
                    currency = rate.currency
            source_key = _source_event_key(device_id, payload)
            event = AccessEvent(
                device_id=device_id,
                device_name=(device.name if device is not None else item["device_name"]),
                device_host=(device.host if device is not None else item["device_host"]),
                device_serial_number=(device.serial_number if device is not None else item["device_serial_number"]),
                station_id=(station.id if station is not None else None),
                station_name=(station.name if station is not None else None),
                card_role=role_code,
                station_user_id=(station_user.id if station_user is not None else None),
                station_user_name=(station_user.name if station_user is not None else None),
                is_billable=is_billable,
                rate_applied=applied_rate,
                currency=currency,
                source_event_key=source_key,
                alarm_type=int(payload.get("alarm_type", 0)),
                event_id=payload.get("event_id"),
                sequence=payload.get("sequence"),
                door_number=payload.get("door_number"),
                door_name=payload.get("door_name"),
                card_number=card_number,
                user_id=payload.get("user_id"),
                cardholder_name=payload.get("cardholder_name"),
                reader_id=payload.get("reader_id"),
                event_direction=payload.get("event_direction") or "UNKNOWN",
                event_type_code=payload.get("event_type_code"),
                open_method=payload.get("open_method"),
                card_type=payload.get("card_type"),
                access_result=access_result,
                raw_status_code=payload.get("raw_status_code"),
                raw_em_status_code=payload.get("raw_em_status_code"),
                error_code=payload.get("error_code"),
                device_event_time=_parse_datetime(payload.get("device_event_time")),
                event_time_utc=_parse_datetime(payload.get("event_time_utc")),
                raw_payload=payload,
                received_at=received_at,
            )
            db.add(event)
            db.commit()
            logger.info(
                "Access event persisted | event_row_id=%s | device_id=%s | card=%s | error_code=%s",
                event.id,
                device_id,
                event.card_number,
                event.error_code,
            )
        except Exception as exc:
            db.rollback()
            # Only events carrying a stable native sequence/event ID are deduplicated.
            # A duplicate callback should not create a second billable event.
            from sqlalchemy.exc import IntegrityError
            if isinstance(exc, IntegrityError) and _source_event_key(item["device_id"], payload):
                logger.info("Duplicate Dahua event ignored | device_id=%s | key=%s", item["device_id"], _source_event_key(item["device_id"], payload))
                return
            raise
        finally:
            db.close()

    def stop(self, timeout: float = 10.0) -> None:
        with self._lock:
            thread = self._thread
            if not self._running or thread is None:
                return
            self._running = False
            try:
                self._queue.put(_STOP, timeout=timeout)
            except queue.Full:
                logger.error("Could not enqueue access-event worker stop marker; pending events may remain.")
                return
        thread.join(timeout=timeout)
        if thread.is_alive():
            logger.warning("Access event worker did not stop before timeout.")
        else:
            logger.info("Access event persistence worker stopped.")
        with self._lock:
            self._thread = None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


event_service = AccessEventService()


def _source_event_key(device_id: int | None, payload: dict[str, Any]) -> str | None:
    """Build an idempotency key only when the SDK provides a stable native ID.

    Do not deduplicate solely by timestamp/card UID: two legitimate taps can
    occur close together and some ASI1201E events expose event_id=0/sequence=None.
    """
    sequence = payload.get("sequence")
    event_id = payload.get("event_id")
    if sequence is None and (event_id is None or int(event_id or 0) <= 0):
        return None
    event_time = payload.get("event_time_utc") or payload.get("device_event_time") or ""
    card_number = str(payload.get("card_number") or "").strip().upper()
    identity = f"{device_id}|{sequence if sequence is not None else ''}|{event_id if event_id is not None else ''}|{event_time}|{card_number}"
    return sha256(identity.encode("utf-8")).hexdigest()
