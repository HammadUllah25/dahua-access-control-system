from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.device import Device
from app.services.dahua_sdk import DahuaSDK, LoginResult, DeviceSubscriptionError
from app.services.secret_store import decrypt_secret

logger = logging.getLogger(__name__)


@dataclass
class DeviceSession:
    handle: int
    connected_at: datetime
    serial_number: str | None
    alarm_listening: bool = False
    subscription_error: str | None = None


class DeviceSessionManager:
    """Holds one SDK login and one alarm-listener state per registered device."""

    def __init__(self) -> None:
        self.sdk = DahuaSDK()
        self._sessions: dict[int, DeviceSession] = {}
        self._lock = threading.RLock()

    def connect(self, device: Device) -> DeviceSession:
        with self._lock:
            existing = self._sessions.get(device.id)
            if existing:
                return existing

            password = decrypt_secret(device.password_encrypted)
            login: LoginResult = self.sdk.login(
                host=device.host,
                port=device.port,
                username=device.username,
                password=password,
            )
            session = DeviceSession(
                handle=login.handle,
                connected_at=datetime.now(timezone.utc),
                serial_number=login.serial_number,
            )
            self._sessions[device.id] = session

            # Capture scalar snapshots rather than retaining an ORM object in a native callback.
            device_id_snapshot = int(device.id)
            device_name_snapshot = device.name
            device_host_snapshot = device.host
            device_serial_snapshot = login.serial_number or device.serial_number

            # Import locally to avoid coupling session management to the event API module.
            from app.services.access_event_service import event_service

            def on_event(payload: dict) -> None:
                event_service.enqueue(
                    device_id=device_id_snapshot,
                    payload=payload,
                    device_name=device_name_snapshot,
                    device_host=device_host_snapshot,
                    device_serial_number=device_serial_snapshot,
                )

            try:
                self.sdk.subscribe_access_events(login.handle, on_event)
                session.alarm_listening = True
                session.subscription_error = None
            except DeviceSubscriptionError as exc:
                # Login/monitoring remain online; the subscription fault is visible in logs.
                session.subscription_error = str(exc)
                logger.exception(
                    "Device login succeeded but access-event subscription failed | device_id=%s",
                    device.id,
                )
            except Exception as exc:
                session.subscription_error = str(exc)
                logger.exception(
                    "Unexpected access-event subscription error | device_id=%s",
                    device.id,
                )

            return session

    def disconnect(self, device_id: int) -> None:
        with self._lock:
            session = self._sessions.pop(device_id, None)
            if session:
                self.sdk.stop_access_events(session.handle)
                self.sdk.logout(session.handle)

    def get_session(self, device_id: int) -> DeviceSession | None:
        with self._lock:
            return self._sessions.get(device_id)

    def is_connected(self, device_id: int) -> bool:
        with self._lock:
            return device_id in self._sessions

    def shutdown(self) -> None:
        with self._lock:
            for device_id in list(self._sessions):
                self.disconnect(device_id)
            self.sdk.cleanup()


sessions = DeviceSessionManager()
