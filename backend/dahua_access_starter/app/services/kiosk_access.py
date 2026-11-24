from __future__ import annotations

import ipaddress
import threading
import time
from fastapi import HTTPException, Request

from app.core.config import (
    KIOSK_ALLOWED_NETWORKS,
    KIOSK_PUBLIC_ENABLED,
    KIOSK_STATION_ID,
)

# Lightweight per-process throttle for the single physical kiosk. For a
# multi-worker deployment, replace this with a shared Redis/database limiter.
_last_create_by_ip: dict[str, float] = {}
_create_lock = threading.Lock()
_CREATE_COOLDOWN_SECONDS = 5.0


def _client_ip(request: Request) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    host = request.client.host if request.client else None
    if not host:
        return None
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def kiosk_request_is_allowed(request: Request, station_id: int) -> bool:
    if not KIOSK_PUBLIC_ENABLED or station_id != KIOSK_STATION_ID:
        return False
    address = _client_ip(request)
    if address is None:
        return False
    for network_text in KIOSK_ALLOWED_NETWORKS:
        try:
            if address in ipaddress.ip_network(network_text, strict=False):
                return True
        except ValueError:
            # Invalid network entries are ignored; the operator should correct
            # the setting before exposing the kiosk on a LAN.
            continue
    return False


def require_kiosk_page_access(request: Request, station_id: int) -> None:
    if not KIOSK_PUBLIC_ENABLED:
        raise HTTPException(status_code=404, detail="Kiosk interface is disabled.")
    if station_id != KIOSK_STATION_ID:
        raise HTTPException(status_code=404, detail="Kiosk station not found.")
    if not kiosk_request_is_allowed(request, station_id):
        raise HTTPException(status_code=403, detail="This kiosk is not available from your network.")


def enforce_kiosk_create_cooldown(request: Request) -> None:
    address = _client_ip(request)
    key = str(address) if address is not None else "unknown"
    now = time.monotonic()
    with _create_lock:
        previous = _last_create_by_ip.get(key)
        if previous is not None and now - previous < _CREATE_COOLDOWN_SECONDS:
            retry_after = max(1, int(_CREATE_COOLDOWN_SECONDS - (now - previous)))
            raise HTTPException(
                status_code=429,
                detail="Please wait a few seconds before creating another payment QR.",
                headers={"Retry-After": str(retry_after)},
            )
        _last_create_by_ip[key] = now
        if len(_last_create_by_ip) > 500:
            cutoff = now - 60.0
            for old_key, timestamp in list(_last_create_by_ip.items()):
                if timestamp < cutoff:
                    _last_create_by_ip.pop(old_key, None)
