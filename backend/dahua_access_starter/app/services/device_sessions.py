from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.device import Device
from app.services.dahua_sdk import DahuaSDK, LoginResult
from app.services.secret_store import decrypt_secret


@dataclass
class DeviceSession:
    handle: int
    connected_at: datetime
    serial_number: str | None


class DeviceSessionManager:
    """Holds one SDK login handle per connected device in this API process."""

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
            return session

    def disconnect(self, device_id: int) -> None:
        with self._lock:
            session = self._sessions.pop(device_id, None)
            if session:
                self.sdk.logout(session.handle)

    def get_session(self, device_id: int) -> DeviceSession | None:
        """Return the current in-process session, if one exists."""
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
