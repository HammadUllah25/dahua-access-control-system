"""SQLite regression smoke test for station roles, rate snapshots and reports.

Run from the project root:
    python tools/station_platform_smoke.py
This test does not connect to a Dahua controller.
"""
from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

try:
    from app.core.database import Base, engine, SessionLocal, ensure_station_platform_columns
    from app.models import Station, Device, StationCardAssignment, StationRate, CashCollection, AccessEvent
    from app.services.access_event_service import AccessEventService
    from app.api.stations import dashboard_summary, usage_report

    Base.metadata.create_all(bind=engine)
    ensure_station_platform_columns()

    today = datetime.now(timezone.utc).date()
    with SessionLocal() as db:
        station = Station(station_code="ST-001", name="Station 001", city="Karachi")
        db.add(station)
        db.flush()
        device = Device(
            name="Station 001 Controller", station_id=station.id,
            connection_type="ip_domain", host="192.0.2.10", port=37777,
            username="admin", password_encrypted="test-only",
            model="ASI1201E", status="pending",
        )
        db.add(device)
        db.flush()
        user_card = StationCardAssignment(
            station_id=station.id, device_id=device.id,
            card_number="FB66983B", card_name="USER Card", role="USER",
            is_billable=True, is_active=True, device_record_no=1001,
            card_type=0, device_card_status=0, is_valid=True,
            valid_from=today, valid_until=date(2037, 12, 31),
            door_indices=[0], time_section_indices=[0], sync_status="synced",
        )
        staff_card = StationCardAssignment(
            station_id=station.id, device_id=device.id,
            card_number="0B56", card_name="STAFF Card", role="STAFF",
            is_billable=False, is_active=True, device_record_no=1002,
            card_type=0, device_card_status=0, is_valid=True,
            valid_from=today, valid_until=date(2037, 12, 31),
            door_indices=[0], time_section_indices=[0], sync_status="synced",
        )
        db.add_all([user_card, staff_card])
        db.add(StationRate(
            station_id=station.id, role="USER", rate_per_use=Decimal("20.00"),
            currency="PKR", effective_from=today,
        ))
        db.add(CashCollection(
            station_id=station.id, period_start=today, period_end=today,
            amount=Decimal("10.00"), currency="PKR",
            collected_at=datetime.now(timezone.utc), received_by="Tester",
        ))
        db.commit()
        station_id = station.id
        device_id = device.id

    writer = AccessEventService()
    common = {
        "device_id": device_id,
        "device_name": "Station 001 Controller",
        "device_host": "192.0.2.10",
        "device_serial_number": "TEST-SERIAL-001",
    }
    writer._persist({
        **common,
        "payload": {
            "alarm_type": 12673, "event_id": 0, "sequence": None,
            "card_number": "FB66983B", "event_direction": "ENTRY",
            "access_result": "granted", "raw_status_code": 1,
            "error_code": 0, "event_time_utc": datetime.now(timezone.utc).isoformat(),
        },
    })
    writer._persist({
        **common,
        "payload": {
            "alarm_type": 12673, "event_id": 0, "sequence": None,
            "card_number": "0B56", "event_direction": "ENTRY",
            "access_result": "granted", "raw_status_code": 1,
            "error_code": 0, "event_time_utc": datetime.now(timezone.utc).isoformat(),
        },
    })

    with SessionLocal() as db:
        events = db.query(AccessEvent).order_by(AccessEvent.id.asc()).all()
        assert len(events) == 2, events
        user_event = next(event for event in events if event.card_number == "FB66983B")
        staff_event = next(event for event in events if event.card_number == "0B56")
        assert user_event.station_id == station_id
        assert user_event.card_role == "USER"
        assert user_event.is_billable is True
        assert Decimal(user_event.rate_applied) == Decimal("20.00")
        assert staff_event.card_role == "STAFF"
        assert staff_event.is_billable is False

        summary = dashboard_summary(
            station_id=station_id, start_date=today, end_date=today, db=db,
        )
        assert summary["user_entries"] == 1, summary
        assert summary["staff_entries"] == 1, summary
        assert summary["billable_entries"] == 1, summary
        assert summary["expected_collection"] == Decimal("20.00"), summary
        assert summary["actual_cash_collected"] == Decimal("10.00"), summary
        assert summary["outstanding_balance"] == Decimal("10.00"), summary

        usage = usage_report(
            group_by="day", station_id=station_id,
            start_date=today, end_date=today, db=db,
        )
        assert len(usage["items"]) == 1, usage
        assert usage["items"][0]["user_entries"] == 1, usage
        assert usage["items"][0]["staff_entries"] == 1, usage

    print("PASS: station card roles are enriched into events; USER entries snapshot the applicable rate; STAFF entries are not billable; dashboard and daily usage report totals reconcile.")
finally:
    try:
        engine.dispose()
    except Exception:
        pass
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass
