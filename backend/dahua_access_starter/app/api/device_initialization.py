from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.device_initialization import (
    DeviceDiscoveryRequest,
    DeviceDiscoveryResponse,
    DeviceInitializeRequest,
    DeviceInitializeResponse,
    LocalInterfaceRead,
)
from app.services.device_initialization import (
    DeviceDiscoveryError,
    DeviceInitializationError,
    initialization_service,
)
from app.services.dahua_sdk import SDKUnavailableError

router = APIRouter(prefix="/device-initialization", tags=["Device Initialization"])


@router.get("/interfaces", response_model=list[LocalInterfaceRead])
def list_local_interfaces():
    """List active local IPv4 addresses available for LAN discovery."""
    return initialization_service.interfaces()


@router.post("/discover", response_model=DeviceDiscoveryResponse)
def discover_devices(payload: DeviceDiscoveryRequest):
    """Discover uninitialized Dahua devices on the selected local network(s)."""
    try:
        result = initialization_service.discover(
            local_ip=payload.local_ip,
            wait_seconds=payload.wait_seconds,
        )
        return result
    except DeviceDiscoveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SDKUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/initialize", response_model=DeviceInitializeResponse)
def initialize_device(payload: DeviceInitializeRequest):
    """Create the first device account on a controller reported as uninitialized."""
    try:
        return initialization_service.initialize_device(
            mac_address=payload.mac_address,
            local_ip=payload.local_ip,
            username=payload.username,
            password=payload.password,
            confirm_password=payload.confirm_password,
            cellphone=payload.cellphone,
            email=payload.email,
        )
    except DeviceInitializationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SDKUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
