from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def device_status_data(device: Any, reason: str | None = None) -> dict[str, Any]:
    """Return the public, credential-free device status representation."""
    last_seen = device.last_tcp_reachable_at or device.last_connected_at
    return {
        "device_id": int(device.id),
        "name": device.name,
        "host": device.host,
        "port": int(device.port),
        "model": device.model,
        "serial_number": device.serial_number,
        "mac_address": device.mac_address,
        "status": device.status,
        "monitoring_enabled": bool(device.monitoring_enabled),
        "last_seen": _iso(last_seen),
        "last_connected_at": _iso(device.last_connected_at),
        "last_health_check_at": _iso(device.last_health_check_at),
        "last_tcp_reachable_at": _iso(device.last_tcp_reachable_at),
        "consecutive_failures": int(device.consecutive_failures or 0),
        "last_error": device.last_error,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
    }


@dataclass(eq=False)
class _Client:
    websocket: WebSocket
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[dict[str, Any]]
    device_id: int | None = None


class DeviceRealtimeHub:
    """Fan out device status events from worker threads to WebSocket clients."""

    def __init__(self, queue_size: int = 100) -> None:
        self._clients: set[_Client] = set()
        self._lock = threading.RLock()
        self._queue_size = max(10, queue_size)

    async def connect(self, websocket: WebSocket, device_id: int | None = None) -> _Client:
        await websocket.accept()
        client = _Client(
            websocket=websocket,
            loop=asyncio.get_running_loop(),
            queue=asyncio.Queue(maxsize=self._queue_size),
            device_id=device_id,
        )
        with self._lock:
            self._clients.add(client)
        return client

    def disconnect(self, client: _Client) -> None:
        with self._lock:
            self._clients.discard(client)

    def publish(self, event: dict[str, Any]) -> None:
        """Safe to call from the monitor's background thread."""
        with self._lock:
            clients = list(self._clients)

        event_device_id = (event.get("data") or {}).get("device_id")
        for client in clients:
            if client.device_id is not None and event_device_id != client.device_id:
                continue
            try:
                client.loop.call_soon_threadsafe(self._enqueue, client, event)
            except RuntimeError:
                self.disconnect(client)

    @staticmethod
    def _enqueue(client: _Client, event: dict[str, Any]) -> None:
        if client.queue.full():
            try:
                client.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            client.queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Dropping device WebSocket event because client queue is full")

    async def next_event(self, client: _Client, timeout_seconds: float = 25.0) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(client.queue.get(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return {
                "type": "heartbeat",
                "data": {"timestamp": datetime.now(timezone.utc).isoformat()},
            }


realtime_hub = DeviceRealtimeHub()


def publish_device_status(device: Any, reason: str) -> None:
    realtime_hub.publish({
        "type": "device.status.changed",
        "data": device_status_data(device, reason=reason),
    })


def publish_device_deleted(device_id: int) -> None:
    realtime_hub.publish({
        "type": "device.deleted",
        "data": {
            "device_id": int(device_id),
            "changed_at": datetime.now(timezone.utc).isoformat(),
        },
    })
