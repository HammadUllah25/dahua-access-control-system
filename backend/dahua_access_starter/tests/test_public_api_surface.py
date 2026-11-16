"""Regression checks for the public API surface in release 1.1.4."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP_DIR = tempfile.TemporaryDirectory(prefix="dahua-api-surface-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(Path(TEMP_DIR.name) / 'api-surface.db').as_posix()}")
os.environ.setdefault("DEVICE_MONITOR_INTERVAL_SECONDS", "600")
os.environ.setdefault("DEVICE_MONITOR_MAX_WORKERS", "1")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_legacy_people_and_network_routers_are_not_mounted():
    paths = app.openapi()["paths"]
    assert "/persons" not in paths
    assert "/persons/{person_id}" not in paths
    assert "/devices/{device_id}/cards" not in paths
    assert "/devices/{device_id}/cards/device-records" not in paths
    assert "/api/network/interfaces" not in paths


def test_required_device_initialization_and_station_user_routes_remain_mounted():
    paths = app.openapi()["paths"]
    assert "/device-initialization/interfaces" in paths
    assert "/device-initialization/discover" in paths
    assert "/device-initialization/initialize" in paths
    assert "/stations/{station_id}/users" in paths
    assert "/stations/{station_id}/users/{user_id}/card-enrollments" in paths
    assert "/devices/status" in paths


def test_removed_routers_return_404_and_initialization_interface_stays_available():
    with TestClient(app) as client:
        assert client.get("/persons").status_code == 404
        assert client.get("/api/network/interfaces").status_code == 404
        # This endpoint is the required interface list used by device initialization.
        response = client.get("/device-initialization/interfaces")
        assert response.status_code == 200, response.text

def test_door_config_operations_are_listed_once_under_door_configuration():
    paths = app.openapi()["paths"]
    for path, method in [
        ("/devices/{device_id}/door-config", "get"),
        ("/devices/{device_id}/door-config", "put"),
    ]:
        operation = paths[path][method]
        assert operation.get("tags") == ["Door Configuration"]

    # The paths remain registered only once in the application router.
    route_matches = [
        route for route in app.routes
        if getattr(route, "path", None) == "/devices/{device_id}/door-config"
    ]
    assert len(route_matches) == 2

