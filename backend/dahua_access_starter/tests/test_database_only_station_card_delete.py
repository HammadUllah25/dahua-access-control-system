"""Offline regression test for database-only station-card deletion.

Run from the project root with:
    python tests/test_database_only_station_card_delete.py

Uses a temporary SQLite database. Dahua SDK/device calls are explicitly guarded
so this test cannot contact or modify a physical controller.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP_DIR = tempfile.TemporaryDirectory(prefix="dahua-db-only-delete-")
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(TEMP_DIR.name) / 'test.db').as_posix()}"
os.environ["DEVICE_MONITOR_INTERVAL_SECONDS"] = "600"
os.environ["DEVICE_MONITOR_MAX_WORKERS"] = "1"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal, seed_operational_roles  # noqa: E402
from app.models.station import Station  # noqa: E402
from app.models.device import Device  # noqa: E402
from app.models.station_card_assignment import StationCardAssignment  # noqa: E402
from app.models.user_card_assignment import UserCardAssignment  # noqa: E402
from app.models.access_event import AccessEvent  # noqa: E402
from app.models.operational_role import OperationalRole  # noqa: E402
from app.models.station_user import StationUser  # noqa: E402
from app.api import stations as stations_api  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    seed_operational_roles()

    db = SessionLocal()
    station = Station(station_code="DBDEL001", name="DB Delete Test", is_active=True)
    db.add(station)
    db.flush()
    device = Device(
        name="Mock controller", station_id=station.id, connection_type="ip_domain",
        host="192.0.2.20", port=37777, username="admin",
        password_encrypted="not-a-real-secret", model="ASI1201E", status="offline",
        inventory_status="in_sync", expected_card_count=2, observed_card_count=2,
    )
    db.add(device)
    db.flush()
    card_1 = StationCardAssignment(
        station_id=station.id, device_id=device.id, card_number="FB66983B",
        card_name="Customer Card 01", role="USER", is_billable=True,
        is_active=True, device_record_no=-77162437, card_type=0,
        device_card_status=0, is_valid=True, door_indices=[0],
        time_section_indices=[0], sync_status="failed",
    )
    card_2 = StationCardAssignment(
        station_id=station.id, device_id=device.id, card_number="41E8",
        card_name="string", role="USER", is_billable=True,
        is_active=False, device_record_no=16872, card_type=0,
        device_card_status=4, is_valid=False, door_indices=[0],
        time_section_indices=[0], sync_status="pending_verification",
    )
    db.add_all([card_1, card_2])
    db.flush()
    station_id, device_id = station.id, device.id
    card_ids = [card_1.id, card_2.id]
    db.add(AccessEvent(
        device_id=device.id, station_id=station.id, alarm_type=1,
        card_number="FB66983B", access_result="granted", event_direction="ENTRY",
        station_name=station.name, station_user_name="Historical User",
        is_billable=True,
    ))
    db.commit()
    db.close()

    # Fail the test if this route ever reaches the hardware operation boundary.
    def forbidden_hardware_call(*_args, **_kwargs):
        raise AssertionError("Database-only deletion attempted a Dahua/device operation")

    stations_api._ensure_connected = forbidden_hardware_call
    stations_api.access_cards.delete_device_card = forbidden_hardware_call
    stations_api.access_cards.update_device_card = forbidden_hardware_call

    with TestClient(app) as client:
        bad_confirmation = client.post(
            f"/stations/{station_id}/cards/database-only-delete",
            json={"assignment_ids": card_ids, "confirmation": "DELETE"},
        )
        assert bad_confirmation.status_code == 422, bad_confirmation.text

        deleted = client.post(
            f"/stations/{station_id}/cards/database-only-delete",
            json={"assignment_ids": card_ids, "confirmation": "DELETE_DATABASE_ONLY"},
        )
        assert deleted.status_code == 200, deleted.text
        result = deleted.json()
        assert result["database_only"] is True
        assert result["controller_contacted"] is False
        assert result["controller_changed"] is False
        assert result["deleted_count"] == 2
        assert result["deleted_assignments"][0]["preserved_access_event_count"] == 1

        listing = client.get(f"/stations/{station_id}/cards")
        assert listing.status_code == 200 and listing.json() == [], listing.text

        db = SessionLocal()
        assert db.query(StationCardAssignment).filter(
            StationCardAssignment.id.in_(card_ids)
        ).count() == 0
        event = db.query(AccessEvent).filter(AccessEvent.card_number == "FB66983B").one()
        assert event.station_user_name == "Historical User"
        current_device = db.get(Device, device_id)
        assert current_device.expected_card_count == 0
        assert current_device.observed_card_count is None
        assert current_device.inventory_status == "verification_required"

        # A card with assignment history must not be hard-deleted.
        role = db.query(OperationalRole).filter(
            OperationalRole.station_id.is_(None), OperationalRole.code == "CUSTOMER"
        ).one()
        user = StationUser(station_id=station_id, name="Test Customer", role_id=role.id)
        db.add(user)
        db.flush()
        history_card = StationCardAssignment(
            station_id=station_id, device_id=device_id, card_number="AABBCCDD",
            card_name="AABBCCDD", role="USER", is_billable=True,
            is_active=True, device_record_no=None, card_type=0,
            device_card_status=0, is_valid=True, door_indices=[0],
            time_section_indices=[0], sync_status="pending",
        )
        db.add(history_card)
        db.flush()
        db.add(UserCardAssignment(
            station_user_id=user.id, station_card_assignment_id=history_card.id,
            station_id=station_id, device_id=device_id, card_number="AABBCCDD",
            is_active=False,
        ))
        db.commit()
        protected_card_id = history_card.id
        db.close()

        blocked = client.post(
            f"/stations/{station_id}/cards/database-only-delete",
            json={"assignment_ids": [protected_card_id], "confirmation": "DELETE_DATABASE_ONLY"},
        )
        assert blocked.status_code == 409, blocked.text
        db = SessionLocal()
        assert db.get(StationCardAssignment, protected_card_id) is not None
        assert db.query(UserCardAssignment).filter(
            UserCardAssignment.station_card_assignment_id == protected_card_id
        ).count() == 1
        db.close()

    print("PASS: database-only deletion removes unlinked station-card rows, preserves access-event history, marks inventory for verification, blocks rows with assignment history, and makes no hardware calls")
    TEMP_DIR.cleanup()


if __name__ == "__main__":
    main()
