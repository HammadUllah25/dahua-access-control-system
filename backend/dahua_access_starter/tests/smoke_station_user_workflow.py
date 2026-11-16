"""Offline smoke test for station-user roles and RFID enrollment.

Run from the project root after: pip install -r requirements-test.txt
The test uses a temporary SQLite database and mocked Dahua SDK calls; it never
connects to or modifies a physical controller or the installation database.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP_DIR = tempfile.TemporaryDirectory(prefix="dahua-station-user-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(TEMP_DIR.name) / 'test.db').as_posix()}"
os.environ["DEVICE_MONITOR_INTERVAL_SECONDS"] = "600"
os.environ["DEVICE_MONITOR_MAX_WORKERS"] = "1"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal, seed_operational_roles, ensure_station_user_event_columns  # noqa: E402
from app.models.station import Station  # noqa: E402
from app.models.device import Device  # noqa: E402
from app.models.access_event import AccessEvent  # noqa: E402
from app.models.operational_role import OperationalRole  # noqa: E402
from app.models.station_user import StationUser  # noqa: E402
from app.models.station_card_assignment import StationCardAssignment  # noqa: E402
from app.models.user_card_assignment import UserCardAssignment  # noqa: E402
from app.models.station_rate import StationRate  # noqa: E402
from app.api import station_users as station_users_api  # noqa: E402
from app.services.card_enrollment import enrollment_service, CardEnrollmentError  # noqa: E402
from app.services.access_event_service import AccessEventService  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_station_user_event_columns()
    seed_operational_roles()

    db = SessionLocal()
    station = Station(station_code="SMOKE001", name="Smoke Test Station", is_active=True)
    db.add(station)
    db.flush()
    device = Device(
        name="Mock ASI1201E", station_id=station.id, connection_type="ip_domain",
        host="192.0.2.10", port=37777, username="admin", password_encrypted="not-a-real-secret",
        model="ASI1201E", status="online", monitoring_enabled=False,
    )
    db.add(device)
    db.commit()
    station_id, device_id = station.id, device.id
    db.close()

    # Replace only the hardware boundary. The API, schemas, SQLAlchemy models,
    # transaction behavior and enrollment-session ownership remain real.
    station_users_api.sessions.is_connected = lambda _device_id: True
    station_users_api.sessions.get_session = lambda _device_id: SimpleNamespace(
        alarm_listening=True, subscription_error=None
    )
    station_users_api.access_cards.add_device_card = lambda *_args, **_kwargs: 9876
    update_calls = []
    def mock_update_device_card(*args, **kwargs):
        update_calls.append((args, kwargs))
        return True
    station_users_api.access_cards.update_device_card = mock_update_device_card

    test_event_time = datetime.now(ZoneInfo("Asia/Karachi"))
    event_time_utc = test_event_time.astimezone(timezone.utc).isoformat()

    with TestClient(app) as client:
        roles_response = client.get(f"/stations/{station_id}/roles")
        assert roles_response.status_code == 200, roles_response.text
        roles = roles_response.json()
        assert {role["code"] for role in roles} == {"MANAGER", "ADMIN", "STAFF", "CUSTOMER"}
        assert {role["code"]: role["default_is_billable"] for role in roles} == {
            "MANAGER": False, "ADMIN": False, "STAFF": False, "CUSTOMER": True
        }
        customer_role = next(role for role in roles if role["code"] == "CUSTOMER")
        system_edit = client.patch(
            f"/stations/{station_id}/roles/{customer_role['id']}", json={"name": "Changed"}
        )
        assert system_edit.status_code == 409, system_edit.text

        custom_response = client.post(
            f"/stations/{station_id}/roles",
            json={"name": "Cleaning Team", "description": "Cleaning personnel", "default_is_billable": False},
        )
        assert custom_response.status_code == 201, custom_response.text
        custom_role = custom_response.json()
        assert custom_role["code"] == "CLEANING_TEAM"
        custom_updated = client.patch(
            f"/stations/{station_id}/roles/{custom_role['id']}",
            json={"description": "Cleaning personnel", "default_is_billable": False},
        )
        assert custom_updated.status_code == 200, custom_updated.text

        user_response = client.post(
            f"/stations/{station_id}/users",
            json={"name": "Ahmed", "phone": "03000000000", "role_id": customer_role["id"]},
        )
        assert user_response.status_code == 201, user_response.text
        user = user_response.json()
        assert user["is_billable"] is True and user["active_card"] is None

        custom_user_response = client.post(
            f"/stations/{station_id}/users",
            json={"name": "Cleaner 1", "role_id": custom_role["id"]},
        )
        assert custom_user_response.status_code == 201, custom_user_response.text
        custom_user = custom_user_response.json()
        assert custom_user["is_billable"] is False

        started = client.post(
            f"/stations/{station_id}/users/{user['id']}/card-enrollments",
            json={"device_id": device_id, "timeout_seconds": 60},
        )
        assert started.status_code == 202, started.text
        token = started.json()["session_token"]
        assert enrollment_service.observe_event(
            device_id, {"card_number": "A1B2C3D4", "access_result": "denied", "error_code": 16}
        )

        poll = client.get(
            f"/stations/{station_id}/users/{user['id']}/card-enrollments/{token}"
        )
        assert poll.status_code == 200 and poll.json()["card_number"] == "A1B2C3D4", poll.text
        wrong_owner_poll = client.get(
            f"/stations/{station_id}/users/{custom_user['id']}/card-enrollments/{token}"
        )
        assert wrong_owner_poll.status_code == 404, wrong_owner_poll.text

        # A station-user token cannot be consumed through the legacy person-based API.
        legacy_poll = client.get(f"/devices/{device_id}/card-enrollments/{token}")
        assert legacy_poll.status_code == 404, legacy_poll.text
        try:
            enrollment_service.claim_for_confirmation(device_id, token)
        except CardEnrollmentError:
            pass
        else:
            raise AssertionError("Legacy person-based confirmation unexpectedly claimed a station-user token")

        confirmed = client.post(
            f"/stations/{station_id}/users/{user['id']}/card-enrollments/{token}/confirm",
            json={
                "card_type": "general", "is_valid": True,
                "valid_from": "2026-11-14", "valid_until": "2037-12-31",
                "door_indices": [0], "time_section_indices": [0],
            },
        )
        assert confirmed.status_code == 201, confirmed.text
        card = confirmed.json()["card"]
        assert confirmed.json()["role"] == "CUSTOMER"
        assert confirmed.json()["is_billable"] is True
        assert card["sync_status"] == "pending_verification"
        assert card["card_name"] == "A1B2C3D4"

        user_detail = client.get(f"/stations/{station_id}/users/{user['id']}")
        assert user_detail.status_code == 200, user_detail.text
        assert user_detail.json()["active_card"]["card_number"] == "A1B2C3D4"

        station_cards = client.get(f"/stations/{station_id}/cards")
        assert station_cards.status_code == 200, station_cards.text
        linked_card = next(row for row in station_cards.json() if row["card_number"] == "A1B2C3D4")
        assert linked_card["station_user_name"] == "Ahmed"
        assert linked_card["operational_role_code"] == "CUSTOMER"

        history = client.get(f"/stations/{station_id}/users/{user['id']}/card-history")
        assert history.status_code == 200 and len(history.json()) == 1, history.text

        second_enrollment = client.post(
            f"/stations/{station_id}/users/{user['id']}/card-enrollments",
            json={"device_id": device_id},
        )
        assert second_enrollment.status_code == 409, second_enrollment.text

        duplicate_link = client.post(
            f"/stations/{station_id}/users/{custom_user['id']}/cards/adopt",
            json={"station_card_assignment_id": card["station_card_assignment_id"]},
        )
        assert duplicate_link.status_code == 409, duplicate_link.text

        # A billable CUSTOMER entry resolves the legacy USER rate bucket.
        db = SessionLocal()
        db.add(StationRate(
            station_id=station_id, role="USER", rate_per_use=125.00, currency="PKR",
            effective_from=test_event_time.date(), effective_until=None,
        ))
        db.commit()
        db.close()
        AccessEventService()._persist({
            "device_id": device_id, "device_name": "Mock ASI1201E", "device_host": "192.0.2.10",
            "device_serial_number": None,
            "payload": {
                "alarm_type": 1, "card_number": "A1B2C3D4", "access_result": "granted",
                "event_direction": "ENTRY", "event_time_utc": event_time_utc,
                "raw_status_code": 0, "raw_em_status_code": 0,
            },
        })
        db = SessionLocal()
        customer_event = db.query(AccessEvent).filter(AccessEvent.card_number == "A1B2C3D4").one()
        assert customer_event.card_role == "CUSTOMER"
        assert customer_event.station_user_name == "Ahmed"
        assert customer_event.is_billable is True
        assert float(customer_event.rate_applied) == 125.0
        db.close()
        customer_events = client.get("/access-events", params={"card_role": "customer"})
        assert customer_events.status_code == 200, customer_events.text
        assert any(row["card_number"] == "A1B2C3D4" for row in customer_events.json())

        revoked = client.delete(f"/stations/{station_id}/users/{user['id']}/card")
        assert revoked.status_code == 200, revoked.text
        user_after_revoke = client.get(f"/stations/{station_id}/users/{user['id']}")
        assert user_after_revoke.status_code == 200 and user_after_revoke.json()["active_card"] is None
        history_after_revoke = client.get(f"/stations/{station_id}/users/{user['id']}/card-history")
        assert history_after_revoke.status_code == 200
        assert len(history_after_revoke.json()) == 1 and history_after_revoke.json()[0]["is_active"] is False

        # Reactivate the same physical card and create a new history link.
        card_assignment_id = card["station_card_assignment_id"]
        reactivated = client.post(
            f"/stations/{station_id}/users/{user['id']}/cards/{card_assignment_id}/activate"
        )
        assert reactivated.status_code == 200, reactivated.text
        assert reactivated.json()["reactivated"] is True
        assert reactivated.json()["card_number"] == "A1B2C3D4"
        assert reactivated.json()["sync_status"] == "pending_verification"
        assert update_calls[-1][1]["is_valid"] is True
        user_after_activate = client.get(f"/stations/{station_id}/users/{user['id']}")
        assert user_after_activate.status_code == 200
        assert user_after_activate.json()["active_card"]["card_number"] == "A1B2C3D4"
        history_after_activate = client.get(f"/stations/{station_id}/users/{user['id']}/card-history")
        assert history_after_activate.status_code == 200
        assert len(history_after_activate.json()) == 2
        assert sum(1 for row in history_after_activate.json() if row["is_active"]) == 1
        duplicate_activate = client.post(
            f"/stations/{station_id}/users/{user['id']}/cards/{card_assignment_id}/activate"
        )
        assert duplicate_activate.status_code == 409, duplicate_activate.text

        # Event processor resolves the physical card -> active user assignment -> role.
        db = SessionLocal()
        custom_role_row = db.get(OperationalRole, custom_role["id"])
        custom_user_row = db.get(StationUser, custom_user["id"])
        second_card = StationCardAssignment(
            station_id=station_id, device_id=device_id, card_number="D4C3B2A1",
            card_name="Cleaner 1", role="STAFF", is_billable=False, is_active=True,
            device_record_no=9877, card_type=0, device_card_status=0, is_valid=True,
            door_indices=[0], time_section_indices=[0], sync_status="pending_verification",
        )
        db.add(second_card)
        db.flush()
        db.add(UserCardAssignment(
            station_user_id=custom_user_row.id, station_card_assignment_id=second_card.id,
            station_id=station_id, device_id=device_id, card_number="D4C3B2A1", is_active=True,
        ))
        db.commit()
        custom_user_id = custom_user_row.id
        db.close()

        AccessEventService()._persist({
            "device_id": device_id, "device_name": "Mock ASI1201E", "device_host": "192.0.2.10",
            "device_serial_number": None,
            "payload": {
                "alarm_type": 1, "card_number": "D4C3B2A1", "access_result": "granted",
                "event_direction": "ENTRY", "event_time_utc": event_time_utc,
                "raw_status_code": 0, "raw_em_status_code": 0,
            },
        })
        db = SessionLocal()
        event = db.query(AccessEvent).filter(AccessEvent.card_number == "D4C3B2A1").one()
        assert event.card_role == custom_role_row.code
        assert event.station_user_id == custom_user_id
        assert event.station_user_name == "Cleaner 1"
        assert event.is_billable is False
        db.close()

    print("PASS: predefined/custom roles, station users, card enrollment, session ownership, one-card rules, card/user reads, assignment history, reactivation, and event-to-user/role resolution")
    TEMP_DIR.cleanup()


if __name__ == "__main__":
    main()
