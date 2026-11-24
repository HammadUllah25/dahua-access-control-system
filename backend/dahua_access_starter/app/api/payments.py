from __future__ import annotations

import base64
import hashlib
import hmac
import io
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import qrcode
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import (
    PAYMENT_ENTRY_FEE_MINOR,
    PAYMENT_QR_TTL_MINUTES,
    SAFEPAY_ENV,
    SAFEPAY_ENABLE_TEST_SIMULATOR,
    KIOSK_DEVICE_ID,
    KIOSK_DOOR_INDEX,
    KIOSK_STATION_ID,
    KIOSK_PUBLIC_ENABLED,
    KIOSK_LOCAL_SIMULATOR_ENABLED,
)
from app.core.database import get_db
from app.models.device import Device
from app.models.payment_transaction import PaymentTransaction
from app.models.station import Station
from app.services.payment_unlock import issue_paid_payment_unlock, mark_sandbox_simulated_capture
from app.services.kiosk_access import (
    enforce_kiosk_create_cooldown,
    kiosk_request_is_allowed,
)
from app.services.safepay_client import SafepayAPIError, safepay_client

router = APIRouter(tags=["Safepay Payments"])


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: int | None = Field(default=None, gt=0)
    door_index: int = Field(default=0, ge=0, le=255)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _authorize_admin_key(value: str | None) -> None:
    import os
    configured = os.getenv("REMOTE_UNLOCK_API_KEY", "").strip()
    if not configured:
        raise HTTPException(503, "Configure REMOTE_UNLOCK_API_KEY before using this administrative endpoint.")
    if not value or not hmac.compare_digest(value, configured):
        raise HTTPException(401, "A valid X-Unlock-API-Key header is required.")


def _authorize_kiosk_key(value: str | None, request: Request, station_id: int) -> bool:
    """Return True for a public kiosk request; otherwise require the admin key."""
    if value:
        _authorize_admin_key(value)
        return False

    if kiosk_request_is_allowed(request, station_id):
        enforce_kiosk_create_cooldown(request)
        return True

    _authorize_admin_key(value)
    return False


def _qr_data_url(payload: str) -> str:
    image = qrcode.make(payload, box_size=8, border=3)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _epoch_to_datetime(value) -> datetime | None:
    if isinstance(value, dict):
        value = value.get("seconds")
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc) if value is not None else None
    except (TypeError, ValueError, OSError):
        return None


def _verify_provider_success(payment: PaymentTransaction, tracker: dict, raast_payment: dict) -> tuple[bool, str]:
    tracker_state = str(tracker.get("state") or "")
    rail_status = str(raast_payment.get("status") or "").upper()
    if tracker.get("token") != payment.tracker_token:
        return False, "TRACKER_MISMATCH"
    totals = tracker.get("purchase_totals") or {}
    quote = totals.get("quote_amount") or {}
    remote_amount = quote.get("amount")
    remote_currency = str(quote.get("currency") or "").upper()
    try:
        amount_matches = int(remote_amount) == payment.amount_minor
    except (TypeError, ValueError):
        amount_matches = False
    if not amount_matches or remote_currency != payment.currency:
        return False, "AMOUNT_OR_CURRENCY_MISMATCH"
    if tracker_state == "TRACKER_ENDED" and rail_status in {"CAPTURED", "SETTLED"}:
        return True, rail_status
    if rail_status in {"FAILED", "REJECTED", "CANCELLED", "REVERSED", "REFUNDED", "PARTIALLY_REFUNDED"}:
        return False, rail_status
    return False, rail_status or tracker_state or "PENDING"


@router.post("/stations/{station_id}/payments/raast-qr", status_code=status.HTTP_201_CREATED)
def create_raast_payment_qr(
    station_id: int,
    payload: PaymentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_unlock_api_key: str | None = Header(default=None, alias="X-Unlock-API-Key"),
):
    """Create a fixed-fee Safepay Raast Dynamic QR for a station door."""
    is_public_kiosk = _authorize_kiosk_key(x_unlock_api_key, request, station_id)
    if is_public_kiosk and station_id != KIOSK_STATION_ID:
        raise HTTPException(404, "Kiosk station not found.")
    station = db.get(Station, station_id)
    if station is None or not station.is_active:
        raise HTTPException(404, "Active station not found.")

    selected_device_id = KIOSK_DEVICE_ID if is_public_kiosk else payload.device_id
    selected_door_index = KIOSK_DOOR_INDEX if is_public_kiosk else payload.door_index
    if selected_device_id is not None:
        device = db.get(Device, selected_device_id)
        if device is None or device.station_id != station_id:
            raise HTTPException(404, "Device not found for this station.")
    else:
        devices = db.query(Device).filter(Device.station_id == station_id).order_by(Device.id.asc()).all()
        if len(devices) != 1:
            raise HTTPException(422, "Configure KIOSK_DEVICE_ID when the station does not have exactly one controller.")
        device = devices[0]

    try:
        provider = safepay_client.create_raast_dynamic_qr(
            amount_minor=PAYMENT_ENTRY_FEE_MINOR,
            expiry_minutes=PAYMENT_QR_TTL_MINUTES,
        )
    except SafepayAPIError as exc:
        raise HTTPException(502, detail=str(exc)) from exc

    raast_payment = provider["raast_payment"]
    expiry = _epoch_to_datetime(raast_payment.get("expires_at")) or (
        _utcnow() + timedelta(minutes=PAYMENT_QR_TTL_MINUTES)
    )
    public_status_token = secrets.token_urlsafe(32)
    payment = PaymentTransaction(
        id=str(uuid.uuid4()),
        station_id=station_id,
        device_id=device.id,
        door_index=selected_door_index,
        provider="SAFEPAY",
        payment_method="RAAST_DYNAMIC_QR",
        environment=SAFEPAY_ENV,
        tracker_token=provider["tracker_token"],
        amount_minor=PAYMENT_ENTRY_FEE_MINOR,
        currency="PKR",
        payment_status="pending",
        provider_status=str(raast_payment.get("status") or "INITIATED"),
        tracker_state=str((provider.get("tracker") or {}).get("state") or "TRACKER_STARTED"),
        unlock_status="not_started",
        qr_payload=provider["qr_payload"],
        qr_expires_at=expiry,
        status_token_hash=_hash_token(public_status_token),
        provider_payload={
            "tracker": provider["tracker_response"],
            "qr": provider["qr_response"],
        },
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {
        "success": True,
        "payment_id": payment.id,
        "status_token": public_status_token,
        "provider": payment.provider,
        "payment_method": payment.payment_method,
        "amount": f"{payment.amount_minor / 100:.2f}",
        "currency": payment.currency,
        "payment_status": payment.payment_status.upper(),
        "unlock_status": payment.unlock_status.upper(),
        "tracker_token": payment.tracker_token,
        "qr_payload": payment.qr_payload,
        "qr_image_data_url": _qr_data_url(payment.qr_payload),
        "expires_at": payment.qr_expires_at.isoformat(),
        "sandbox": SAFEPAY_ENV == "sandbox",
        "note": "Safepay sandbox Raast QR is simulated and cannot be paid from a banking app.",
    }


@router.post("/stations/{station_id}/payments/local-simulate")
def create_local_simulated_payment(
    station_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Local-development-only test payment. Never contacts Safepay or accepts money."""
    import ipaddress
    if SAFEPAY_ENV != "sandbox" or not KIOSK_LOCAL_SIMULATOR_ENABLED:
        raise HTTPException(404, "Local payment simulator is disabled.")
    if station_id != KIOSK_STATION_ID or not KIOSK_PUBLIC_ENABLED:
        raise HTTPException(404, "Kiosk station not found.")
    client_host = request.client.host if request.client else ""
    try:
        is_loopback = ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        raise HTTPException(403, "Local simulator is available only from the FastAPI host computer.")
    enforce_kiosk_create_cooldown(request)
    station = db.get(Station, station_id)
    if station is None or not station.is_active:
        raise HTTPException(404, "Active station not found.")
    device_id = KIOSK_DEVICE_ID
    if device_id is None:
        devices = db.query(Device).filter(Device.station_id == station_id).order_by(Device.id.asc()).all()
        if len(devices) != 1:
            raise HTTPException(422, "Configure KIOSK_DEVICE_ID when the station does not have exactly one controller.")
        device_id = devices[0].id
    device = db.get(Device, device_id)
    if device is None or device.station_id != station_id:
        raise HTTPException(404, "Configured device not found for this station.")
    public_status_token = secrets.token_urlsafe(32)
    payment_id = str(uuid.uuid4())
    local_reference = "LOCAL-TEST-NOT-A-REAL-PAYMENT-" + payment_id
    payment = PaymentTransaction(
        id=payment_id, station_id=station_id, device_id=device.id, door_index=KIOSK_DOOR_INDEX,
        provider="LOCAL_TEST", payment_method="LOCAL_SIMULATED", environment="sandbox",
        tracker_token=local_reference, amount_minor=PAYMENT_ENTRY_FEE_MINOR, currency="PKR",
        payment_status="pending", provider_status="LOCAL_TEST_PENDING", tracker_state="LOCAL_TEST_CREATED",
        unlock_status="not_started", qr_payload=local_reference,
        qr_expires_at=_utcnow() + timedelta(minutes=2), status_token_hash=_hash_token(public_status_token),
        provider_payload={"test_simulation": {"type": "LOCAL_ONLY", "note": "No Safepay request and no money collected."}},
    )
    db.add(payment)
    db.commit()
    payment.payment_status = "paid_test"
    payment.provider_status = "LOCAL_SIMULATED_CAPTURE"
    payment.tracker_state = "LOCAL_TEST_PAYMENT_CONFIRMED"
    payment.paid_at = _utcnow()
    payment.provider_payload = {
        **(payment.provider_payload or {}),
        "test_simulation": {"type": "LOCAL_ONLY", "note": "No Safepay request and no money collected."},
    }
    db.commit()
    result = issue_paid_payment_unlock(db, payment.id, test_simulation=True)
    db.refresh(payment)
    return {
        "success": bool(result.get("success")), "payment_id": payment.id,
        "status_token": public_status_token, "payment_status": payment.payment_status.upper(),
        "unlock_status": payment.unlock_status.upper(), "amount": f"{payment.amount_minor / 100:.2f}",
        "currency": payment.currency, "expires_at": payment.qr_expires_at.isoformat(),
        "test_mode": "LOCAL_ONLY", "message": result.get("message"),
        "warning": "LOCAL TEST ONLY: Safepay was not contacted and no payment was collected.",
    }


@router.get("/payments/{payment_id}/status")
def get_payment_status(
    payment_id: str,
    x_payment_access_token: str | None = Header(default=None, alias="X-Payment-Access-Token"),
    db: Session = Depends(get_db),
):
    payment = db.get(PaymentTransaction, payment_id)
    if payment is None:
        raise HTTPException(404, "Payment transaction not found.")
    if not x_payment_access_token or not hmac.compare_digest(
        _hash_token(x_payment_access_token), payment.status_token_hash
    ):
        raise HTTPException(401, "A valid X-Payment-Access-Token header is required.")

    if payment.payment_status == "pending":
        try:
            provider_response = safepay_client.get_tracker_status(payment.tracker_token)
        except SafepayAPIError as exc:
            raise HTTPException(503, detail=f"Safepay status could not be checked. Retry shortly. {exc}") from exc
        tracker = (provider_response.get("data") or {}).get("tracker") or {}
        raast_payment = tracker.get("raast_payment") or {}
        success, provider_status = _verify_provider_success(payment, tracker, raast_payment)
        payment.provider_status = provider_status
        payment.tracker_state = str(tracker.get("state") or payment.tracker_state or "")
        payment.provider_payload = {**(payment.provider_payload or {}), "latest_status": provider_response}
        if success:
            payment.payment_status = "paid"
            payment.paid_at = _utcnow()
            db.commit()
            issue_paid_payment_unlock(db, payment.id)
        elif provider_status in {"FAILED", "REJECTED", "CANCELLED", "REVERSED", "REFUNDED", "PARTIALLY_REFUNDED"}:
            payment.payment_status = "failed"
            db.commit()
        elif payment.qr_expires_at:
            expiry = payment.qr_expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if _utcnow() >= expiry:
                payment.payment_status = "expired"
                db.commit()

    # Recovery: if payment was committed as paid but the process stopped before
    # claiming the unlock, a later kiosk poll safely resumes the one-time claim.
    db.refresh(payment)
    if payment.payment_status == "paid" and payment.unlock_status == "not_started":
        issue_paid_payment_unlock(db, payment.id)

    db.refresh(payment)
    return {
        "payment_id": payment.id,
        "payment_status": payment.payment_status.upper(),
        "provider_status": payment.provider_status,
        "tracker_state": payment.tracker_state,
        "unlock_status": payment.unlock_status.upper(),
        "amount": f"{payment.amount_minor / 100:.2f}",
        "currency": payment.currency,
        "access_event_id": payment.access_event_id,
        "physical_door_state_verified": False if payment.unlock_status == "command_accepted" else None,
        "message": (
            "Payment confirmed; Dahua accepted the unlock command."
            if payment.unlock_status == "command_accepted"
            else "Payment is confirmed, but door unlocking needs attention."
            if payment.payment_status in {"paid", "paid_test"}
            else "Waiting for Safepay payment confirmation."
            if payment.payment_status == "pending"
            else f"Payment is {payment.payment_status}."
        ),
    }


@router.post("/payments/{payment_id}/sandbox-simulate-capture")
def simulate_sandbox_capture(
    payment_id: str,
    x_unlock_api_key: str | None = Header(default=None, alias="X-Unlock-API-Key"),
    db: Session = Depends(get_db),
):
    """DEVELOPMENT ONLY: simulate a paid sandbox transaction to exercise the Dahua unlock path."""
    _authorize_admin_key(x_unlock_api_key)
    if SAFEPAY_ENV != "sandbox" or not SAFEPAY_ENABLE_TEST_SIMULATOR:
        raise HTTPException(404, "Sandbox simulator is disabled.")
    payment = db.get(PaymentTransaction, payment_id)
    if payment is None:
        raise HTTPException(404, "Payment transaction not found.")
    try:
        result = mark_sandbox_simulated_capture(db, payment)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {
        **result,
        "warning": "TEST SIMULATION ONLY. Safepay did not confirm or collect money.",
    }
