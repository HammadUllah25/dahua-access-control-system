from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


class CardEnrollmentError(RuntimeError):
    pass


@dataclass
class EnrollmentSession:
    token: str
    device_id: int
    created_at: datetime
    expires_at: datetime
    status: str = "waiting"
    card_number: str | None = None
    captured_at: datetime | None = None
    event_payload: dict[str, Any] = field(default_factory=dict)


class CardEnrollmentService:
    """In-memory one-card-at-a-time enrollment listener per registered controller."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, EnrollmentSession] = {}
        self._active_by_device: dict[int, str] = {}

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    def _refresh_expiry(self, item: EnrollmentSession) -> None:
        if item.status == "waiting" and self._utcnow() >= item.expires_at:
            item.status = "expired"
            self._active_by_device.pop(item.device_id, None)

    @staticmethod
    def _serialize(item: EnrollmentSession) -> dict[str, Any]:
        return {
            "session_token": item.token,
            "device_id": item.device_id,
            "status": item.status,
            "card_number": item.card_number,
            "created_at": item.created_at.isoformat(),
            "expires_at": item.expires_at.isoformat(),
            "captured_at": item.captured_at.isoformat() if item.captured_at else None,
            "event_access_result": item.event_payload.get("access_result"),
            "event_error_code": item.event_payload.get("error_code"),
            "event_door_number": item.event_payload.get("door_number"),
            "message": {
                "waiting": "Present an IC card to the selected Dahua reader.",
                "captured": "Card UID captured. Review it and confirm the assignment.",
                "confirming": "The captured card is being registered.",
                "confirmed": "The card and person profile were registered.",
                "expired": "Enrollment timed out before a card was captured.",
                "cancelled": "Card enrollment was cancelled.",
            }.get(item.status, item.status),
        }

    def _prune_old_sessions(self, now: datetime) -> None:
        cutoff = now - timedelta(hours=24)
        for token, item in list(self._sessions.items()):
            if item.created_at < cutoff and item.status in {"confirmed", "expired", "cancelled"}:
                self._sessions.pop(token, None)

    def begin(self, device_id: int, timeout_seconds: int = 90) -> dict[str, Any]:
        now = self._utcnow()
        device_id = int(device_id)
        with self._lock:
            self._prune_old_sessions(now)
            active_token = self._active_by_device.get(device_id)
            if active_token:
                active = self._sessions.get(active_token)
                if active:
                    self._refresh_expiry(active)
                    if active.status in {"waiting", "captured", "confirming"}:
                        raise CardEnrollmentError(
                            f"Device already has an active card enrollment session ({active.status}). "
                            "Complete or cancel it before starting another."
                        )
                self._active_by_device.pop(device_id, None)

            token = uuid.uuid4().hex
            item = EnrollmentSession(
                token=token,
                device_id=device_id,
                created_at=now,
                expires_at=now + timedelta(seconds=int(timeout_seconds)),
            )
            self._sessions[token] = item
            self._active_by_device[device_id] = token
            return self._serialize(item)

    def observe_event(self, device_id: int, payload: dict[str, Any]) -> bool:
        """Capture the first event containing a card UID for this device."""
        card_number = str(payload.get("card_number") or "").strip().upper()
        if not card_number:
            return False
        with self._lock:
            token = self._active_by_device.get(int(device_id))
            item = self._sessions.get(token) if token else None
            if item is None:
                return False
            self._refresh_expiry(item)
            if item.status != "waiting":
                return False
            item.card_number = card_number
            item.captured_at = self._utcnow()
            # This payload contains only event metadata; no credential PIN/password is stored here.
            item.event_payload = {
                key: payload.get(key)
                for key in (
                    "event_id", "event_direction", "event_type_code",
                    "access_result", "error_code", "door_number", "door_name",
                    "reader_id", "event_time_utc", "device_event_time",
                )
            }
            item.status = "captured"
            return True

    def get(self, device_id: int, token: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._sessions.get(str(token))
            if item is None or item.device_id != int(device_id):
                return None
            self._refresh_expiry(item)
            return self._serialize(item)

    def claim_for_confirmation(self, device_id: int, token: str) -> EnrollmentSession:
        with self._lock:
            item = self._sessions.get(str(token))
            if item is None or item.device_id != int(device_id):
                raise CardEnrollmentError("Card enrollment session was not found.")
            self._refresh_expiry(item)
            if item.status != "captured" or not item.card_number:
                raise CardEnrollmentError(
                    f"Card cannot be confirmed while enrollment status is '{item.status}'."
                )
            item.status = "confirming"
            return item

    def confirmation_failed(self, device_id: int, token: str) -> None:
        with self._lock:
            item = self._sessions.get(str(token))
            if item and item.device_id == int(device_id) and item.status == "confirming":
                item.status = "captured"

    def confirmation_succeeded(self, device_id: int, token: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._sessions.get(str(token))
            if item is None or item.device_id != int(device_id):
                return None
            item.status = "confirmed"
            self._active_by_device.pop(item.device_id, None)
            return self._serialize(item)

    def cancel(self, device_id: int, token: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._sessions.get(str(token))
            if item is None or item.device_id != int(device_id):
                return None
            if item.status == "confirming":
                raise CardEnrollmentError("Cannot cancel while card registration is in progress.")
            if item.status not in {"confirmed", "expired"}:
                item.status = "cancelled"
            self._active_by_device.pop(item.device_id, None)
            return self._serialize(item)


enrollment_service = CardEnrollmentService()
