"""A removed RFID card can be scanned again and given to a new station user.

Flow: assign card to user A -> remove card -> delete user A -> scan same card for user B.
Uses a temporary SQLite database and mocked Dahua SDK calls; no controller is contacted.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP_DIR = tempfile.TemporaryDirectory(prefix="dahua-card-reuse-", ignore_cleanup_errors=True)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(Path(TEMP_DIR.name) / 'card-reuse.db').as_posix()}")
os.environ.setdefault("DEVICE_MONITOR_INTERVAL_SECONDS", "600")
os.environ.setdefault("DEVICE_MONITOR_MAX_WORKERS", "1")

from fastapi.testclient import TestClient  # noqa: E402

from app.api import station_users as station_users_api  # noqa: E402
from app.core.config import DATABASE_URL  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.device import Device  # noqa: E402
from app.models.station import Station  # noqa: E402
from app.services.card_enrollment import enrollment_service  # noqa: E402

CARD = "A1B2C3D4"
CONFIRM = {
    "card_type": "general", "is_valid": True,
    "valid_from": "2026-11-14", "valid_until": "2037-12-31",
    "door_indices": [0], "time_section_indices": [0],
}


def _enroll(client: TestClient, station_id: int, user_id: int, device_id: int):
    started = client.post(
        f"/stations/{station_id}/users/{user_id}/card-enrollments",
        json={"device_id": device_id, "timeout_seconds": 60},
    )
    assert started.status_code == 202, started.text
    token = started.json()["session_token"]
    assert enrollment_service.observe_event(device_id, {"card_number": CARD, "access_result": "denied"})
    return client.post(f"/stations/{station_id}/users/{user_id}/card-enrollments/{token}/confirm", json=CONFIRM)


def test_removed_card_is_reused_for_a_new_user(monkeypatch):
    assert "card-reuse" in DATABASE_URL or "dahua-" in DATABASE_URL, "refusing to run against the installation database"
    adds, updates = [], []
    monkeypatch.setattr(station_users_api.sessions, "is_connected", lambda _id: True)
    monkeypatch.setattr(
        station_users_api.sessions, "get_session",
        lambda _id: SimpleNamespace(alarm_listening=True, subscription_error=None),
    )
    monkeypatch.setattr(station_users_api.access_cards, "add_device_card", lambda *a, **k: adds.append(k) or 9876)
    monkeypatch.setattr(station_users_api.access_cards, "update_device_card", lambda *a, **k: updates.append((a, k)))

    with TestClient(app) as client:
        db = SessionLocal()
        station = Station(station_code="REUSE01", name="Reuse Station", is_active=True)
        db.add(station)
        db.flush()
        device = Device(
            name="Mock ASI1201E", station_id=station.id, connection_type="ip_domain",
            host="192.0.2.20", port=37777, username="admin", password_encrypted="x",
            model="ASI1201E", status="online", monitoring_enabled=False,
        )
        db.add(device)
        db.commit()
        station_id, device_id = station.id, device.id
        db.close()

        role_id = client.get(f"/stations/{station_id}/roles").json()[0]["id"]
        new_user = lambda name: client.post(f"/stations/{station_id}/users", json={"name": name, "role_id": role_id}).json()["id"]
        user_a, user_b, user_c = new_user("Old Owner"), new_user("New Owner"), new_user("Other")

        first = _enroll(client, station_id, user_a, device_id)
        assert first.status_code == 201, first.text
        card_id = first.json()["card"]["id"]

        assert client.delete(f"/stations/{station_id}/users/{user_a}/card").status_code == 200
        assert updates[-1][1]["is_valid"] is False
        assert client.delete(f"/stations/{station_id}/users/{user_a}").status_code == 200

        reused = _enroll(client, station_id, user_b, device_id)
        assert reused.status_code == 201, reused.text
        assert reused.json()["card"]["id"] == card_id, "the existing card record should be reused"
        assert len(adds) == 1, "no second controller insert for a reused card"
        args, kwargs = updates[-1]
        assert args == (device_id, 9876) and kwargs["is_valid"] is True

        # While the card is active on the new owner, nobody else can take it.
        taken = _enroll(client, station_id, user_c, device_id)
        assert taken.status_code == 409, taken.text
