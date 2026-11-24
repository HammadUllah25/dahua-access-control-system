from __future__ import annotations

from fastapi import HTTPException
from starlette.requests import Request

from app.services import kiosk_access


def _request(host: str) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/kiosk/1",
        "raw_path": b"/kiosk/1",
        "query_string": b"",
        "headers": [],
        "client": (host, 54321),
        "server": ("testserver", 8000),
    }
    return Request(scope)


def test_public_kiosk_access_is_enabled_station_and_network_scoped(monkeypatch):
    monkeypatch.setattr(kiosk_access, "KIOSK_PUBLIC_ENABLED", True)
    monkeypatch.setattr(kiosk_access, "KIOSK_STATION_ID", 1)
    monkeypatch.setattr(kiosk_access, "KIOSK_ALLOWED_NETWORKS", ("127.0.0.1/32", "192.168.10.0/24"))

    assert kiosk_access.kiosk_request_is_allowed(_request("192.168.10.24"), 1)
    assert not kiosk_access.kiosk_request_is_allowed(_request("192.168.11.24"), 1)
    assert not kiosk_access.kiosk_request_is_allowed(_request("192.168.10.24"), 2)


def test_kiosk_page_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(kiosk_access, "KIOSK_PUBLIC_ENABLED", False)
    try:
        kiosk_access.require_kiosk_page_access(_request("127.0.0.1"), 1)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Disabled kiosk page should return 404")


def test_kiosk_payment_creation_has_a_short_per_ip_cooldown(monkeypatch):
    monkeypatch.setattr(kiosk_access, "_CREATE_COOLDOWN_SECONDS", 5.0)
    kiosk_access._last_create_by_ip.clear()
    request = _request("192.168.10.25")

    kiosk_access.enforce_kiosk_create_cooldown(request)
    try:
        kiosk_access.enforce_kiosk_create_cooldown(request)
    except HTTPException as exc:
        assert exc.status_code == 429
        assert "Retry-After" in exc.headers
    else:
        raise AssertionError("Second immediate QR creation should be throttled")
    finally:
        kiosk_access._last_create_by_ip.clear()


def test_customer_kiosk_does_not_contain_master_unlock_key_or_simulator_call():
    from pathlib import Path

    page = (Path(__file__).resolve().parents[1] / "app" / "static" / "kiosk.html").read_text(encoding="utf-8")
    assert "X-Unlock-API-Key" not in page
    assert "sandbox-simulate-capture" not in page
    assert "/payments/" in page
    assert "qr_image_data_url" in page
