from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

from app.api.remote_unlock import router as remote_unlock_router
from app.api.qr_access import router as qr_access_router
from app.api.devices import (
    router as devices_router,
    door_config_router as door_config_router,
)
from app.api.device_initialization import router as device_initialization_router
from app.api.access_events import router as access_events_router
from app.api.realtime import router as realtime_router
from app.api.stations import router as stations_router
from app.api.station_users import router as station_users_router
from app.api.payments import router as payments_router
from app.core.config import APP_NAME, PAYMENT_ENTRY_FEE_MINOR, KIOSK_LOCAL_SIMULATOR_ENABLED, SAFEPAY_ENV
from app.core.database import (
    Base,
    engine,
    ensure_device_monitoring_columns,
    ensure_person_import_columns,
    ensure_access_card_import_columns,
    ensure_device_identity_columns,
    ensure_station_platform_columns,
    ensure_station_user_event_columns,
    ensure_access_event_source_columns,
    seed_operational_roles,
)
from app.models import (
    Device, Person, AccessCard, AccessEvent, Station, StationCardAssignment,
    StationRate, CashCollection, DeviceSyncJob, OperationalRole, StationUser, UserCardAssignment,
)  # noqa: F401 - register model metadata
from app.services.access_event_service import event_service
from app.services.device_sessions import sessions
from app.services.device_monitor import monitor
from app.services.kiosk_access import require_kiosk_page_access


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_device_monitoring_columns()
    ensure_person_import_columns()
    ensure_access_card_import_columns()
    ensure_device_identity_columns()
    ensure_station_platform_columns()
    ensure_station_user_event_columns()
    ensure_access_event_source_columns()
    seed_operational_roles()
    event_service.start()
    monitor.start()
    yield
    monitor.stop()
    sessions.shutdown()
    event_service.stop()


app = FastAPI(
    title=APP_NAME,
    version="1.1.6",
    description=(
        "API for Dahua access-controller registration, LAN initialization, monitoring, "
        "station operational users and predefined/custom roles linked to RFID cards, "
        "usage and cash reporting, "
        "device inventory checks and controlled cloud-to-device recovery."
    ),
    lifespan=lifespan,
)

app.include_router(devices_router)
app.include_router(remote_unlock_router)
app.include_router(qr_access_router)
app.include_router(door_config_router)
app.include_router(device_initialization_router)
# Legacy People/IC Card and standalone Network routers are intentionally not mounted.
# Their underlying models/services remain in the package for database compatibility.
app.include_router(access_events_router)
app.include_router(realtime_router)
app.include_router(stations_router)
app.include_router(station_users_router)
app.include_router(payments_router)


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


_DASHBOARD_FILE = Path(__file__).resolve().parent / "static" / "dashboard.html"


@app.get("/dashboard-ui", include_in_schema=False)
def dashboard_ui():
    return FileResponse(_DASHBOARD_FILE)


_KIOSK_FILE = Path(__file__).resolve().parent / "static" / "kiosk.html"


@app.get("/kiosk/{station_id}", response_class=HTMLResponse, include_in_schema=False)
def kiosk_ui(station_id: int, request: Request):
    """Serve the public, LAN-restricted customer payment kiosk."""
    require_kiosk_page_access(request, station_id)
    if not _KIOSK_FILE.is_file():
        return HTMLResponse("Kiosk interface file is missing.", status_code=500)
    html = _KIOSK_FILE.read_text(encoding="utf-8")
    html = html.replace("__KIOSK_ENTRY_FEE__", f"{PAYMENT_ENTRY_FEE_MINOR / 100:.2f}")
    html = html.replace("__KIOSK_STATION_ID__", str(station_id))
    html = html.replace("__LOCAL_SIMULATOR_ENABLED__", "true" if KIOSK_LOCAL_SIMULATOR_ENABLED and SAFEPAY_ENV == "sandbox" else "false")
    return HTMLResponse(html)
