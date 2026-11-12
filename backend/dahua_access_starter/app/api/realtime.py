from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.device import Device
from app.services.realtime import device_status_data, realtime_hub

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Realtime"])


def _snapshot(device_id: int | None = None) -> dict:
    db: Session = SessionLocal()
    try:
        query = db.query(Device)
        if device_id is not None:
            query = query.filter(Device.id == device_id)
        devices = query.order_by(Device.id.asc()).all()
        items = [device_status_data(device) for device in devices]
        counts = {"online": 0, "offline": 0, "pending": 0, "total": len(items)}
        for item in items:
            key = item["status"] if item["status"] in counts else None
            if key is not None:
                counts[key] += 1
        return {
            "type": "device.status.snapshot",
            "data": {
                "devices": items,
                "summary": counts,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    finally:
        db.close()


@router.websocket("/ws/devices")
async def device_status_websocket(websocket: WebSocket, device_id: int | None = None):
    """Stream a status snapshot followed by device status changes.

    Optional query parameter: ?device_id=123
    """
    client = await realtime_hub.connect(websocket, device_id=device_id)
    sender: asyncio.Task | None = None
    receiver: asyncio.Task | None = None

    async def send_events() -> None:
        while True:
            event = await realtime_hub.next_event(client)
            await websocket.send_json(event)

    async def receive_client_messages() -> None:
        while True:
            message = await websocket.receive_text()
            try:
                parsed = json.loads(message)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict) and parsed.get("type") == "ping":
                realtime_hub._enqueue(client, {
                    "type": "pong",
                    "data": {"timestamp": datetime.now(timezone.utc).isoformat()},
                })

    try:
        await websocket.send_json(_snapshot(device_id=device_id))
        sender = asyncio.create_task(send_events())
        receiver = asyncio.create_task(receive_client_messages())
        done, pending = await asyncio.wait(
            {sender, receiver}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            exception = task.exception()
            if exception:
                raise exception
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("Device WebSocket closed", exc_info=True)
    finally:
        for task in (sender, receiver):
            if task and not task.done():
                task.cancel()
        realtime_hub.disconnect(client)
