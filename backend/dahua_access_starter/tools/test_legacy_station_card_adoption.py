"""Offline regression test for adopting legacy person-based cards into station roles.

Run from the project root:
    python tools/test_legacy_station_card_adoption.py

No Dahua SDK call or physical controller connection is made.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

try:
    from fastapi import HTTPException
    from app.core.database import Base, engine, SessionLocal
    from app.models import Station, Device, Person, AccessCard, StationCardAssignment
    from app.schemas.stations import (
        StationCardAdoptRequest,
        ReprovisionRequest,
        ManualReprovisionVerificationRequest,
    )
    from app.api import stations as station_api
    from app.api.stations import adopt_existing_person_card

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        station = Station(station_code="ST-ADOPT", name="Adoption Test Station")
        db.add(station)
        db.flush()
        device = Device(
            name="Test ASI1201E", station_id=station.id,
            connection_type="ip_domain", host="192.0.2.20", port=37777,
            username="admin", password_encrypted="test-only",
            model="ASI1201E", status="online",
        )
        person = Person(person_code="LEGACY-01", name="Legacy Person")
        db.add_all([device, person])
        db.flush()
        legacy_user = AccessCard(
            person_id=person.id, device_id=device.id,
            card_number="FB66983B", card_name="Old Customer Card",
            device_record_no=1234, card_type=0, device_card_status=0,
            is_valid=True, valid_from=date(2026, 11, 12),
            valid_until=date(2037, 12, 31),
            door_indices=[0], time_section_indices=[0], sync_status="synced",
        )
        legacy_staff = AccessCard(
            person_id=person.id, device_id=device.id,
            card_number="0B56", card_name="Old Test Card",
            device_record_no=1235, card_type=0, device_card_status=0,
            is_valid=True, valid_from=date(2026, 11, 12),
            valid_until=date(2037, 12, 31),
            door_indices=[0], time_section_indices=[0], sync_status="synced",
        )
        db.add_all([legacy_user, legacy_staff])
        db.commit()

        user_assignment = adopt_existing_person_card(
            station.id,
            StationCardAdoptRequest(
                device_id=device.id, card_number="fb66983b", role="USER",
                card_name="Customer Card 01",
            ),
            db,
        )
        assert user_assignment.role == "USER"
        assert user_assignment.is_billable is True
        assert user_assignment.card_number == "FB66983B"
        assert user_assignment.device_record_no is None
        assert user_assignment.sync_status == "needs_reprovisioning"

        staff_assignment = adopt_existing_person_card(
            station.id,
            StationCardAdoptRequest(
                device_id=device.id, card_number="0b56", role="STAFF",
            ),
            db,
        )
        assert staff_assignment.role == "STAFF"
        assert staff_assignment.is_billable is False
        assert staff_assignment.card_name == "Old Test Card"

        # Existing person/card rows remain untouched and available for compatibility.
        assert db.query(Person).count() == 1
        assert db.query(AccessCard).count() == 2
        assert db.query(StationCardAssignment).count() == 2
        assert db.get(Device, device.id).inventory_status == "needs_reprovisioning"
        assert db.get(Device, device.id).expected_card_count == 2

        try:
            adopt_existing_person_card(
                station.id,
                StationCardAdoptRequest(device_id=device.id, card_number="FB66983B", role="USER"),
                db,
            )
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("Duplicate station adoption should return HTTP 409")

        # Simulate controller inserts succeeding but ASI1201E inventory readback
        # being unsupported. A second confirmed restore must be blocked to avoid
        # inserting duplicate native card records.
        insert_calls: list[str] = []
        station_api.sessions.is_connected = lambda _device_id: True
        station_api.access_cards.add_device_card = lambda _device_id, **kwargs: (
            insert_calls.append(kwargs["card_number"]) or (7000 + len(insert_calls))
        )

        def unsupported_inventory(_device_id):
            raise station_api.AccessCardSDKError("FindRecord is not supported by this firmware")

        station_api.access_cards.list_device_cards = unsupported_inventory
        restore_result = station_api.reprovision_device_from_cloud(
            device.id,
            ReprovisionRequest(
                confirmation="REPROVISION_FROM_CLOUD",
                controller_confirmed_factory_reset=True,
            ),
            db,
        )
        assert restore_result["status"] == "verification_required", restore_result
        assert set(insert_calls) == {"FB66983B", "0B56"}, insert_calls

        try:
            station_api.reprovision_device_from_cloud(
                device.id,
                ReprovisionRequest(
                    confirmation="REPROVISION_FROM_CLOUD",
                    controller_confirmed_factory_reset=True,
                ),
                db,
            )
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("A repeated confirmed restore must be blocked")
        assert len(insert_calls) == 2, insert_calls

        manual_result = station_api.confirm_manual_reprovision_verification(
            device.id,
            ManualReprovisionVerificationRequest(
                confirmation="I_VERIFIED_EACH_CARD_IN_SMARTPSS_AND_TESTED_ACCESS",
                verified_card_numbers=["fb66983b", "0b56"],
            ),
            db,
        )
        assert manual_result["status"] == "succeeded", manual_result
        assert all(item.sync_status == "synced" for item in db.query(StationCardAssignment).all())

    print("PASS: legacy adoption preserves old records; confirmed restore is single-attempt safe when SDK readback is unsupported; manual SmartPSS/physical verification can close the recovery job.")
finally:
    try:
        engine.dispose()
    except Exception:
        pass
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass
