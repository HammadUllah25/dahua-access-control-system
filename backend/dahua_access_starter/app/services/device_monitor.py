from __future__ import annotations

import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import (
    DEVICE_MONITOR_FAILURE_THRESHOLD,
    DEVICE_MONITOR_INTERVAL_SECONDS,
    DEVICE_MONITOR_MAX_WORKERS,
    DEVICE_MONITOR_RECONNECT_COOLDOWN_SECONDS,
    DEVICE_MONITOR_TCP_TIMEOUT_SECONDS,
)
from app.models.device import Device
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError
from app.services.device_sessions import sessions
from app.services.realtime import publish_device_status

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def tcp_port_is_reachable(host: str, port: int, timeout: float) -> tuple[bool, str | None]:
    """Check whether the device's TCP service is reachable.

    This is a network reachability test, not a full authentication or SDK-session
    health test. A successful SDK login is additionally required for Online.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, None
    except (OSError, TimeoutError) as exc:
        return False, str(exc)


class DeviceMonitor:
    """Single-process background monitor for registered Dahua controllers.

    The monitor checks the configured TCP port, debounces transient failures,
    releases stale SDK sessions, and logs in again after connectivity returns.
    Run one API process only; move this service to dedicated/sharded workers
    before deploying a large fleet.
    """

    def __init__(
        self,
        interval_seconds: float = 10.0,
        tcp_timeout_seconds: float = 1.5,
        failure_threshold: int = 2,
        reconnect_cooldown_seconds: float = 30.0,
        max_workers: int = 32,
    ) -> None:
        self.interval_seconds = max(2.0, interval_seconds)
        self.tcp_timeout_seconds = max(0.2, tcp_timeout_seconds)
        self.failure_threshold = max(1, failure_threshold)
        self.reconnect_cooldown_seconds = max(5.0, reconnect_cooldown_seconds)
        self.max_workers = max(1, max_workers)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._last_cycle_at: datetime | None = None
        self._last_cycle_duration_ms: float | None = None
        self._last_cycle_device_count = 0
        self._last_cycle_error: str | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="dahua-device-monitor",
                daemon=True,
            )
            self._thread.start()
            logger.info("Device monitor started (interval=%ss)", self.interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(5.0, self.interval_seconds + 2.0))
        self._thread = None
        logger.info("Device monitor stopped")

    def status(self) -> dict[str, Any]:
        thread = self._thread
        return {
            "enabled": True,
            "running": bool(thread and thread.is_alive()),
            "interval_seconds": self.interval_seconds,
            "tcp_timeout_seconds": self.tcp_timeout_seconds,
            "failure_threshold": self.failure_threshold,
            "reconnect_cooldown_seconds": self.reconnect_cooldown_seconds,
            "max_workers": self.max_workers,
            "last_cycle_at": self._last_cycle_at,
            "last_cycle_duration_ms": self._last_cycle_duration_ms,
            "last_cycle_device_count": self._last_cycle_device_count,
            "last_cycle_error": self._last_cycle_error,
            "online_definition": "TCP port reachable and this process holds a NetSDK login handle",
            "note": (
                "TCP reachability plus a local SDK session handle; this is not a device-originated "
                "heartbeat subscription. Use dedicated sharded workers for large fleets."
            ),
        }

    def check_device_now(self, device_id: int) -> dict[str, Any]:
        """Run one immediate health check; used by the manual-check endpoint."""
        return self._check_device(device_id)

    def _run(self) -> None:
        # Run once immediately at startup, then wait between completed scans.
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                device_ids = self._enabled_device_ids()
                self._last_cycle_device_count = len(device_ids)
                if device_ids:
                    with ThreadPoolExecutor(max_workers=min(self.max_workers, len(device_ids))) as pool:
                        list(pool.map(self._check_device_safely, device_ids))
                self._last_cycle_error = None
            except Exception as exc:  # keep the monitor alive after one bad cycle
                self._last_cycle_error = str(exc)
                logger.exception("Device monitor cycle failed")

            self._last_cycle_at = utc_now()
            self._last_cycle_duration_ms = round((time.monotonic() - started) * 1000, 2)
            elapsed = time.monotonic() - started
            self._stop_event.wait(max(0.1, self.interval_seconds - elapsed))

    def _enabled_device_ids(self) -> list[int]:
        db: Session = SessionLocal()
        try:
            return [
                int(device_id)
                for (device_id,) in db.query(Device.id)
                .filter(Device.monitoring_enabled.is_(True))
                .order_by(Device.id.asc())
                .all()
            ]
        finally:
            db.close()

    def _check_device_safely(self, device_id: int) -> None:
        try:
            self._check_device(device_id)
        except Exception:
            logger.exception("Health check failed unexpectedly for device_id=%s", device_id)

    def _check_device(self, device_id: int) -> dict[str, Any]:
        db: Session = SessionLocal()
        try:
            device = db.get(Device, device_id)
            if device is None:
                return {"device_id": device_id, "result": "not_found"}
            if not device.monitoring_enabled:
                return {"device_id": device_id, "result": "monitoring_disabled"}

            previous_status = device.status
            reachable, probe_error = tcp_port_is_reachable(
                device.host,
                device.port,
                self.tcp_timeout_seconds,
            )
            now = utc_now()
            device.last_health_check_at = now

            if not reachable:
                device.consecutive_failures = int(device.consecutive_failures or 0) + 1
                if device.consecutive_failures >= self.failure_threshold:
                    # Close a possibly stale NetSDK handle after debounced failure.
                    sessions.disconnect(device.id)
                    device.status = "offline"
                    device.last_error = (
                        f"Health check failed: TCP {device.host}:{device.port} is unreachable. "
                        f"{probe_error or ''}".strip()
                    )
                db.commit()
                if device.status != previous_status:
                    publish_device_status(device, reason="monitor_unreachable")
                return {
                    "device_id": device.id,
                    "result": "unreachable",
                    "status": device.status,
                    "consecutive_failures": device.consecutive_failures,
                    "error": probe_error,
                }

            device.last_tcp_reachable_at = now
            device.consecutive_failures = 0

            # A process restart loses in-memory sessions, so reconnect even if
            # the persisted database status still says online.
            needs_login = device.status != "online" or not sessions.is_connected(device.id)
            if not needs_login:
                device.last_error = None
                db.commit()
                return {
                    "device_id": device.id,
                    "result": "reachable_session_held",
                    "status": "online",
                }

            last_attempt = device.last_connect_attempt_at
            # SQLite commonly returns timezone-aware SQLAlchemy DateTime values
            # as naive datetimes. Treat those stored UTC values as UTC before
            # subtracting them from the current aware UTC timestamp.
            if last_attempt is not None and last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(tzinfo=timezone.utc)
            due = (
                last_attempt is None
                or (now - last_attempt).total_seconds() >= self.reconnect_cooldown_seconds
            )
            if not due:
                db.commit()
                return {
                    "device_id": device.id,
                    "result": "reachable_reconnect_backoff",
                    "status": device.status,
                }

            device.last_connect_attempt_at = now
            db.commit()

            try:
                session = sessions.connect(device)
                device.status = "online"
                device.serial_number = session.serial_number or device.serial_number
                device.last_connected_at = session.connected_at
                device.last_error = None
                device.consecutive_failures = 0
                db.commit()
                if device.status != previous_status:
                    publish_device_status(device, reason="monitor_reconnected")
                return {
                    "device_id": device.id,
                    "result": "reconnected",
                    "status": "online",
                    "serial_number": device.serial_number,
                }
            except (SDKUnavailableError, DeviceLoginError, ValueError) as exc:
                device.status = "offline"
                device.last_error = str(exc)
                db.commit()
                if device.status != previous_status:
                    publish_device_status(device, reason="monitor_login_failed")
                return {
                    "device_id": device.id,
                    "result": "login_failed",
                    "status": "offline",
                    "error": str(exc),
                }
        finally:
            db.close()


monitor = DeviceMonitor(
    interval_seconds=DEVICE_MONITOR_INTERVAL_SECONDS,
    tcp_timeout_seconds=DEVICE_MONITOR_TCP_TIMEOUT_SECONDS,
    failure_threshold=DEVICE_MONITOR_FAILURE_THRESHOLD,
    reconnect_cooldown_seconds=DEVICE_MONITOR_RECONNECT_COOLDOWN_SECONDS,
    max_workers=DEVICE_MONITOR_MAX_WORKERS,
)
