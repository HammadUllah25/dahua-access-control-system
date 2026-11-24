from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import SAFEPAY_ENV, SAFEPAY_ENABLE_TEST_SIMULATOR
from app.models.device import Device
from app.models.payment_transaction import PaymentTransaction
from app.services.device_sessions import sessions
from app.services.remote_access_events import record_remote_unlock_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def issue_paid_payment_unlock(db: Session, payment_id: str, *, test_simulation: bool = False) -> dict:
    """Claim one paid transaction and issue no more than one remote-open command."""
    payment = db.get(PaymentTransaction, payment_id)
    if payment is None:
        return {"success": False, "message": "Payment transaction not found."}

    is_real_paid = payment.payment_status == "paid"
    is_test_paid = payment.payment_status == "paid_test"
    if not is_real_paid and not (test_simulation and is_test_paid):
        return {"success": False, "payment_status": payment.payment_status, "unlock_status": payment.unlock_status}

    # This conditional UPDATE is the idempotency gate. Only the request that
    # changes not_started -> processing is allowed to call the physical device.
    result = db.execute(
        update(PaymentTransaction)
        .where(
            PaymentTransaction.id == payment_id,
            PaymentTransaction.unlock_status == "not_started",
            PaymentTransaction.payment_status == ("paid_test" if is_test_paid else "paid"),
        )
        .values(unlock_status="processing", unlock_started_at=_utcnow())
    )
    db.commit()
    if result.rowcount != 1:
        db.refresh(payment)
        return {
            "success": payment.unlock_status == "command_accepted",
            "payment_status": payment.payment_status,
            "unlock_status": payment.unlock_status,
            "message": "Unlock has already been claimed or processed; no second command was sent.",
        }

    device = db.get(Device, payment.device_id)
    if device is None:
        payment.unlock_status = "failed"
        db.commit()
        return {"success": False, "payment_status": payment.payment_status, "unlock_status": "failed", "message": "Configured door controller no longer exists."}

    try:
        command_result = sessions.open_door(
            device,
            door_index=payment.door_index,
            operator_id="SAFEPAY_RAAST_TEST" if is_test_paid else "SAFEPAY_RAAST",
        )
    except Exception as exc:
        event = record_remote_unlock_event(
            db,
            device=device,
            door_index=payment.door_index,
            user_type="CUSTOMER",
            operator_id="SAFEPAY_RAAST_TEST" if is_test_paid else "SAFEPAY_RAAST",
            reason="SANDBOX_PAYMENT_TEST" if is_test_paid else "PAYMENT_CONFIRMED",
            command_status="failed",
            payment_reference=payment.tracker_token,
            error=str(exc),
        )
        payment.unlock_status = "failed"
        payment.access_event_id = event.id
        db.commit()
        return {
            "success": False,
            "payment_status": payment.payment_status,
            "unlock_status": "failed",
            "event_id": event.id,
            "message": f"Payment is recorded, but the Dahua unlock command failed: {exc}",
        }

    event = record_remote_unlock_event(
        db,
        device=device,
        door_index=payment.door_index,
        user_type="CUSTOMER",
        operator_id="SAFEPAY_RAAST_TEST" if is_test_paid else "SAFEPAY_RAAST",
        reason="SANDBOX_PAYMENT_TEST" if is_test_paid else "PAYMENT_CONFIRMED",
        command_status="command_accepted",
        payment_reference=payment.tracker_token,
        sdk_result=command_result.get("sdk_result"),
    )
    payment.unlock_status = "command_accepted"
    payment.access_event_id = event.id
    payment.unlocked_at = _utcnow()
    db.commit()
    return {
        "success": True,
        "payment_status": payment.payment_status,
        "unlock_status": "command_accepted",
        "event_id": event.id,
        "sdk_result": command_result.get("sdk_result"),
        "physical_door_state_verified": False,
        "message": "Dahua accepted the remote-open command. Physical door movement is not independently verified.",
        "test_simulation": is_test_paid,
    }


def mark_sandbox_simulated_capture(db: Session, payment: PaymentTransaction) -> dict:
    """Mark a payment as a clearly labelled local sandbox simulation, never a real Safepay capture."""
    if SAFEPAY_ENV != "sandbox" or not SAFEPAY_ENABLE_TEST_SIMULATOR:
        raise RuntimeError("Sandbox payment simulator is disabled. It can only run when SAFEPAY_ENV=sandbox and SAFEPAY_ENABLE_TEST_SIMULATOR=true.")
    if payment.environment != "sandbox" or payment.payment_status != "pending":
        raise RuntimeError("Only a pending sandbox payment can be simulated.")
    payment.payment_status = "paid_test"
    payment.provider_status = "SANDBOX_SIMULATED_CAPTURE"
    payment.tracker_state = "TEST_SIMULATED_TRACKER_ENDED"
    payment.paid_at = _utcnow()
    payload = dict(payment.provider_payload or {})
    payload["test_simulation"] = {
        "type": "LOCAL_SANDBOX_SIMULATED_CAPTURE",
        "created_at": _utcnow().isoformat(),
        "note": "Not a Safepay-confirmed payment and not real money.",
    }
    payment.provider_payload = payload
    db.commit()
    return issue_paid_payment_unlock(db, payment.id, test_simulation=True)
