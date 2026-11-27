"""Inventory check repairs a stored controller record number from the controller's own list.

Site case: card FB66983B was stored with record number -77162437; the controller holds it as
record 7. After one inventory check the database points at record 7, so revoke/delete work.
Temporary SQLite database and mocked SDK calls; no controller is contacted.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP_DIR = tempfile.TemporaryDirectory(prefix="dahua-inventory-", ignore_cleanup_errors=True)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(Path(TEMP_DIR.name) / 'inventory.db').as_posix()}")
os.environ.setdefault("DEVICE_MONITOR_INTERVAL_SECONDS", "600")
os.environ.setdefault("DEVICE_MONITOR_MAX_WORKERS", "1")

from fastapi.testclient import TestClient  # noqa: E402

from app.api import stations as stations_api  # noqa: E402
from app.core.config import DATABASE_URL  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.device import Device  # noqa: E402
from app.models.station import Station  # noqa: E402
from app.models.station_card_assignment import StationCardAssignment  # noqa: E402


def test_inventory_check_repairs_wrong_record_number(monkeypatch):
    assert Path(tempfile.gettempdir()).as_posix().lower() in DATABASE_URL.lower(), "refusing to run outside a temp database"
    monkeypatch.setattr(stations_api.sessions, "is_connected", lambda _id: True)
    monkeypatch.setattr(
        stations_api.access_cards, "list_device_cards",
        lambda _device_id, **_k: [
            {"record_number": 7, "card_number": "FB66983B"},
            {"record_number": 8, "card_number": "0000BEEF"},
        ],
    )

    with TestClient(app) as client:
        db = SessionLocal()
        station = Station(station_code=f"INV{os.getpid()}", name="Inventory Station", is_active=True)
        db.add(station)
        db.flush()
        device = Device(
            name="Mock ASI1201E", station_id=station.id, connection_type="ip_domain",
            host="192.0.2.30", port=37777, username="admin", password_encrypted="x",
            model="ASI1201E", status="online", monitoring_enabled=False,
        )
        db.add(device)
        db.flush()
        card = StationCardAssignment(
            station_id=station.id, device_id=device.id, card_number="FB66983B", card_name="FB66983B",
            role="USER", is_billable=True, is_active=True, device_record_no=-77162437, card_type=0,
            device_card_status=0, is_valid=True, valid_from=date(2026, 1, 1), valid_until=date(2037, 12, 31),
            door_indices=[0], time_section_indices=[0], sync_status="failed",
        )
        db.add(card)
        db.commit()
        device_id, card_id = device.id, card.id
        db.close()

        res = client.post(f"/devices/{device_id}/inventory-check")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["repaired_record_numbers"] == ["FB66983B"]
        assert body["missing_cards"] == [] and body["unexpected_cards"] == ["0000BEEF"]

        db = SessionLocal()
        assert db.get(StationCardAssignment, card_id).device_record_no == 7
        db.close()
