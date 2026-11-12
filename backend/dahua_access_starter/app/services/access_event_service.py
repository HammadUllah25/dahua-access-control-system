from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime
from typing import Any

from app.core.database import SessionLocal
from app.models.access_event import AccessEvent
from app.models.device import Device

logger = logging.getLogger(__name__)
_STOP = object()


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
            event = AccessEvent(
                device_id=device_id,
                device_name=(device.name if device is not None else item["device_name"]),
                device_host=(device.host if device is not None else item["device_host"]),
                device_serial_number=(device.serial_number if device is not None else item["device_serial_number"]),
                alarm_type=int(payload.get("alarm_type", 0)),
                event_id=payload.get("event_id"),
                sequence=payload.get("sequence"),
                door_number=payload.get("door_number"),
                door_name=payload.get("door_name"),
                card_number=payload.get("card_number"),
                user_id=payload.get("user_id"),
                cardholder_name=payload.get("cardholder_name"),
                reader_id=payload.get("reader_id"),
                event_direction=payload.get("event_direction") or "UNKNOWN",
                event_type_code=payload.get("event_type_code"),
                open_method=payload.get("open_method"),
                card_type=payload.get("card_type"),
                access_result=payload.get("access_result") or "unknown",
                raw_status_code=payload.get("raw_status_code"),
                raw_em_status_code=payload.get("raw_em_status_code"),
                error_code=payload.get("error_code"),
                device_event_time=_parse_datetime(payload.get("device_event_time")),
                event_time_utc=_parse_datetime(payload.get("event_time_utc")),
                raw_payload=payload,
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
        except Exception:
            db.rollback()
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
