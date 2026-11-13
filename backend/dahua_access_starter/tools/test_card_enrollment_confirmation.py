from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import people_cards
from app.schemas.card_enrollment import CardEnrollmentConfirm


def _person():
    return SimpleNamespace(id=7, name="Hammad", person_code="tXIt9YRlhd", department="cs", phone="03000000000")


def _assignment():
    return {
        "id": 55,
        "person_id": 7,
        "device_id": 1,
        "card_number": "FB66983B",
        "card_name": "Hammad RFID Card",
        "device_record_no": 1001,
        "card_type": 0,
        "device_card_status": 0,
        "is_valid": True,
        "valid_from": date(2026, 11, 12),
        "valid_until": date(2037, 12, 31),
        "door_indices": [0],
        "time_section_indices": [0],
        "sync_status": "synced",
        "last_sync_error": None,
        "last_synced_at": None,
    }


def test_confirm_uses_card_assignment_path_not_personnel_service(monkeypatch):
    person = _person()
    captured = SimpleNamespace(card_number="FB66983B")
    calls = {"write": None, "succeeded": False, "failed": False}

    monkeypatch.setattr(people_cards, "_person_or_404", lambda db, person_id: person)
    monkeypatch.setattr(people_cards.enrollment_service, "claim_for_confirmation", lambda d, t: captured)
    monkeypatch.setattr(people_cards.enrollment_service, "confirmation_succeeded", lambda d, t: calls.__setitem__("succeeded", True))
    monkeypatch.setattr(people_cards.enrollment_service, "confirmation_failed", lambda d, t: calls.__setitem__("failed", True))

    def write_assignment(device_id, payload, db):
        calls["write"] = (device_id, payload)
        return _assignment()

    monkeypatch.setattr(people_cards, "_write_card_assignment", write_assignment)

    def forbidden(*args, **kwargs):
        raise AssertionError("The ASI1201E confirmation flow must not call personnel-service APIs.")

    monkeypatch.setattr(people_cards.access_cards, "add_device_user", forbidden, raising=False)
    monkeypatch.setattr(people_cards.access_cards, "delete_device_user", forbidden, raising=False)

    payload = CardEnrollmentConfirm(
        person_id=7,
        card_name="Hammad RFID Card",
        card_type="general",
        is_valid=True,
        valid_from=date(2026, 11, 12),
        valid_until=date(2037, 12, 31),
        door_indices=[0],
        time_section_indices=[0],
    )
    result = people_cards.confirm_card_enrollment(1, "test-token", payload, db=object())

    assert calls["write"] is not None
    device_id, card_payload = calls["write"]
    assert device_id == 1
    assert card_payload.person_id == 7
    assert card_payload.card_number == "FB66983B"
    assert calls["succeeded"] is True
    assert calls["failed"] is False
    assert result["person_id"] == 7
    assert result["card"]["card_number"] == "FB66983B"


def test_failed_card_write_restores_captured_session(monkeypatch):
    person = _person()
    captured = SimpleNamespace(card_number="FB66983B")
    calls = {"failed": False}

    monkeypatch.setattr(people_cards, "_person_or_404", lambda db, person_id: person)
    monkeypatch.setattr(people_cards.enrollment_service, "claim_for_confirmation", lambda d, t: captured)
    monkeypatch.setattr(people_cards.enrollment_service, "confirmation_failed", lambda d, t: calls.__setitem__("failed", True))
    monkeypatch.setattr(people_cards, "_write_card_assignment", lambda *args: (_ for _ in ()).throw(HTTPException(status_code=502, detail="simulated device write failure")))

    payload = CardEnrollmentConfirm(person_id=7)
    with pytest.raises(HTTPException) as exc_info:
        people_cards.confirm_card_enrollment(1, "test-token", payload, db=object())

    assert exc_info.value.status_code == 502
    assert calls["failed"] is True


def test_shared_assignment_helper_saves_person_card_link_after_device_insert(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base
    from app.models.access_card import AccessCard
    from app.models.device import Device
    from app.models.person import Person
    from app.schemas.access_card import AccessCardCreate

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    device_calls = []

    monkeypatch.setattr(people_cards, "_ensure_connected", lambda device, db: None)

    def fake_device_insert(device_id, **kwargs):
        device_calls.append((device_id, kwargs))
        return 77

    monkeypatch.setattr(people_cards.access_cards, "add_device_card", fake_device_insert)

    with TestSession() as db:
        person = Person(person_code="TEST-001", name="Hammad", department="cs")
        device = Device(
            name="Test ASI1201E",
            connection_type="ip_domain",
            host="192.0.2.10",
            port=37777,
            username="admin",
            password_encrypted="test-only-not-a-real-secret",
            model="ASI1201E",
        )
        db.add_all([person, device])
        db.commit()
        db.refresh(person)
        db.refresh(device)

        payload = AccessCardCreate(
            person_id=person.id,
            card_number="FB66983B",
            card_name="Hammad RFID Card",
            card_type="general",
            is_valid=True,
            valid_from=date(2026, 11, 12),
            valid_until=date(2037, 12, 31),
            door_indices=[0],
            time_section_indices=[0],
        )
        assignment = people_cards._write_card_assignment(device.id, payload, db)

        assert len(device_calls) == 1
        assert device_calls[0][0] == device.id
        assert device_calls[0][1]["card_number"] == "FB66983B"
        assert assignment.device_record_no == 77
        saved = db.query(AccessCard).filter(AccessCard.device_id == device.id).one()
        assert saved.person_id == person.id
        assert saved.card_number == "FB66983B"
        assert saved.sync_status == "synced"

    engine.dispose()


def test_asi1201e_personnel_lookup_is_explicitly_not_supported(monkeypatch):
    device = SimpleNamespace(model="DHI-ASI1201E")
    monkeypatch.setattr(people_cards, "_device_or_404", lambda db, device_id: device)

    with pytest.raises(HTTPException) as exc_info:
        people_cards.get_controller_person_record(1, "tXIt9YRlhd", db=object())

    assert exc_info.value.status_code == 501
    assert "GET /persons" in exc_info.value.detail


def test_asi1201e_card_listing_does_not_call_personnel_service(monkeypatch):
    device = SimpleNamespace(model="ASI1201E")
    rows = [{"record_number": 77, "card_number": "FB66983B", "device_user_id": "optional-user-id"}]
    monkeypatch.setattr(people_cards, "_device_or_404", lambda db, device_id: device)
    monkeypatch.setattr(people_cards, "_ensure_connected", lambda device, db: None)
    monkeypatch.setattr(people_cards.access_cards, "list_device_cards", lambda device_id: rows)

    def forbidden(*args, **kwargs):
        raise AssertionError("ASI1201E card listing must not call the optional personnel service.")

    monkeypatch.setattr(people_cards.access_cards, "get_device_user_records", forbidden)
    result = people_cards.list_controller_cards(1, db=object())

    assert result[0]["card_number"] == "FB66983B"
    assert result[0]["person_profile"] is None
    assert result[0]["person_profile_error"] is None
