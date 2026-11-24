from __future__ import annotations

from types import SimpleNamespace

from app.api.payments import _verify_provider_success


def _payment():
    return SimpleNamespace(
        tracker_token="track_sandbox_123",
        amount_minor=100,
        currency="PKR",
    )


def test_safepay_capture_is_accepted_only_for_matching_tracker_amount_and_currency():
    payment = _payment()
    tracker = {
        "token": "track_sandbox_123",
        "state": "TRACKER_ENDED",
        "purchase_totals": {"quote_amount": {"currency": "PKR", "amount": 100}},
    }
    accepted, status = _verify_provider_success(payment, tracker, {"status": "CAPTURED"})
    assert accepted is True
    assert status == "CAPTURED"


def test_initiated_qr_is_not_treated_as_paid():
    tracker = {
        "token": "track_sandbox_123",
        "state": "TRACKER_STARTED",
        "purchase_totals": {"quote_amount": {"currency": "PKR", "amount": 100}},
    }
    accepted, status = _verify_provider_success(_payment(), tracker, {"status": "INITIATED"})
    assert accepted is False
    assert status == "INITIATED"


def test_mismatched_amount_is_not_accepted_even_if_tracker_ended():
    tracker = {
        "token": "track_sandbox_123",
        "state": "TRACKER_ENDED",
        "purchase_totals": {"quote_amount": {"currency": "PKR", "amount": 10000}},
    }
    accepted, status = _verify_provider_success(_payment(), tracker, {"status": "CAPTURED"})
    assert accepted is False
    assert status == "AMOUNT_OR_CURRENCY_MISMATCH"


def test_mismatched_tracker_is_not_accepted():
    tracker = {
        "token": "track_someone_elses_payment",
        "state": "TRACKER_ENDED",
        "purchase_totals": {"quote_amount": {"currency": "PKR", "amount": 100}},
    }
    accepted, status = _verify_provider_success(_payment(), tracker, {"status": "CAPTURED"})
    assert accepted is False
    assert status == "TRACKER_MISMATCH"
