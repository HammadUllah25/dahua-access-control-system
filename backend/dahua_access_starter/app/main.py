from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.devices import router as devices_router
from app.api.device_initialization import router as device_initialization_router
from app.api.people_cards import router as people_cards_router
from app.api.network import router as network_router
from app.api.access_events import router as access_events_router
from app.api.realtime import router as realtime_router
from app.core.config import APP_NAME
from app.core.database import (
    Base,
    engine,
    ensure_device_monitoring_columns,
    ensure_person_import_columns,
    ensure_access_card_import_columns,
    ensure_device_identity_columns,
)
from app.models import Device, Person, AccessCard, AccessEvent  # noqa: F401 - register model metadata
from app.services.access_event_service import event_service
from app.services.device_sessions import sessions
from app.services.device_monitor import monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_device_monitoring_columns()
    ensure_person_import_columns()
    ensure_access_card_import_columns()
    ensure_device_identity_columns()
    event_service.start()
    monitor.start()
    yield
    monitor.stop()
    sessions.shutdown()
    event_service.stop()


app = FastAPI(
    title=APP_NAME,
    version="0.9.0",
    description=(
        "API for Dahua access-controller registration, LAN initialization, monitoring, "
        "people and IC-card management, timed RFID card enrollment, Ethernet adapter discovery, "
        "and persisted access events."
    ),
    lifespan=lifespan,
)

app.include_router(devices_router)
app.include_router(device_initialization_router)
app.include_router(people_cards_router)
app.include_router(network_router)
app.include_router(access_events_router)
app.include_router(realtime_router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": APP_NAME}


@app.get("/sdk/status", tags=["System"])
def sdk_status():
    try:
        import NetSDK  # noqa: F401
        installed = True
        error = None
    except Exception as exc:
        installed = False
        error = str(exc)
    return {
        "python_sdk_importable": installed,
        "initialized": sessions.sdk._initialized,
        "error": error,
        "note": "SDK is initialized lazily when device discovery or the first device connection is requested.",
        "device_monitor_running": monitor.status()["running"],
        "event_persistence_running": event_service._running,
    }
