from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

import qrcode
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import PUBLIC_API_BASE_URL, QR_ACCESS_TTL_SECONDS
from app.core.database import get_db
from app.models.device import Device
from app.models.qr_access_grant import QRAccessGrant
from app.models.station import Station
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError
from app.services.device_sessions import sessions
from app.services.remote_access_events import record_remote_unlock_event

router = APIRouter(tags=["Customer QR Access"])


class QRAccessCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: int | None = Field(default=None, gt=0)
    door_index: int = Field(default=0, ge=0, le=255)


class QRAccessRedeemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=200)


def _authorize_qr_management(x_unlock_api_key: str | None) -> None:
    configured = os.getenv("REMOTE_UNLOCK_API_KEY", "").strip()
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="QR issuance is disabled. Configure REMOTE_UNLOCK_API_KEY and restart the API.",
        )
    if not x_unlock_api_key or not hmac.compare_digest(x_unlock_api_key, configured):
        raise HTTPException(status_code=401, detail="A valid X-Unlock-API-Key header is required.")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _qr_data_url(value: str) -> str:
    image = qrcode.make(value, box_size=8, border=3)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@router.post("/stations/{station_id}/qr-access-sessions", status_code=status.HTTP_201_CREATED)
def create_customer_qr_access(
    station_id: int,
    payload: QRAccessCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_unlock_api_key: str | None = Header(default=None, alias="X-Unlock-API-Key"),
):
    """Create a one-minute, one-use rotating QR authorization for a station door.

    This endpoint is for a trusted station display/kiosk, not the customer's browser.
    """
    _authorize_qr_management(x_unlock_api_key)
    station = db.get(Station, station_id)
    if station is None or not station.is_active:
        raise HTTPException(status_code=404, detail="Active station not found.")

    if payload.device_id is not None:
        device = db.get(Device, payload.device_id)
        if device is None or device.station_id != station_id:
            raise HTTPException(status_code=404, detail="Device not found for this station.")
    else:
        devices = db.query(Device).filter(Device.station_id == station_id).order_by(Device.id.asc()).all()
        if len(devices) != 1:
            raise HTTPException(
                status_code=422,
                detail="Provide device_id when the station has zero or multiple registered controllers.",
            )
        device = devices[0]

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=QR_ACCESS_TTL_SECONDS)
    grant = QRAccessGrant(
        token_hash=_token_hash(token),
        station_id=station_id,
        device_id=device.id,
        door_index=payload.door_index,
        status="issued",
        created_at=now,
        expires_at=expires_at,
    )
    db.add(grant)
    db.commit()

    base_url = PUBLIC_API_BASE_URL or str(request.base_url).rstrip("/")
    qr_url = f"{base_url}/qr-access/claim?token={token}"
    return {
        "success": True,
        "station_id": station.id,
        "station_name": station.name,
        "device_id": device.id,
        "device_name": device.name,
        "door_index": payload.door_index,
        "authorization_type": "CUSTOMER_QR_TEMPORARY",
        "single_use": True,
        "expires_in_seconds": QR_ACCESS_TTL_SECONDS,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "qr_url": qr_url,
        "qr_image_data_url": _qr_data_url(qr_url),
        "note": "Display this QR for one minute. The customer scans it and confirms Unlock on the page. Generate a new QR after expiry or redemption.",
    }


@router.get("/qr-access/claim", response_class=HTMLResponse, include_in_schema=False)
def qr_access_claim_page(token: str = Query(..., min_length=20, max_length=200)):
    """Small mobile-friendly confirmation page opened by scanning the station QR."""
    token_json = json.dumps(token)
    html = f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Station Access</title>
<style>body{{font-family:Arial,sans-serif;background:#f4f6f8;display:grid;place-items:center;min-height:100vh;margin:0}}main{{background:white;padding:28px;border-radius:16px;max-width:360px;width:calc(100% - 56px);box-shadow:0 8px 30px #0001;text-align:center}}button{{background:#1769aa;color:white;border:0;border-radius:10px;padding:14px 22px;font-size:17px;width:100%;cursor:pointer}}button:disabled{{opacity:.5}}#status{{margin-top:18px;color:#333;line-height:1.5}}</style></head>
<body><main><h2>Customer Door Access</h2><p>Press below to request one-time access. This QR authorization expires after one minute.</p><button id=\"unlock\">Unlock Door</button><div id=\"status\" role=\"status\"></div></main>
<script>const token={token_json};const button=document.getElementById('unlock');const out=document.getElementById('status');button.addEventListener('click',async()=>{{button.disabled=true;out.textContent='Requesting access…';try{{const response=await fetch('/qr-access/redeem',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{token}})}});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Access could not be authorized.');out.textContent='Your access request was accepted. Please open the door.';}}catch(error){{out.textContent=error.message;button.disabled=false;}}}});</script></body></html>"""
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.post("/qr-access/redeem")
def redeem_customer_qr_access(
    payload: QRAccessRedeemRequest,
    db: Session = Depends(get_db),
):
    """Atomically consume a QR token once, then issue the Dahua remote-open command."""
    token_hash = _token_hash(payload.token)
    now = datetime.now(timezone.utc)
    grant = db.query(QRAccessGrant).filter(QRAccessGrant.token_hash == token_hash).first()
    if grant is None:
        raise HTTPException(status_code=404, detail="QR authorization not found or invalid.")

    claim = db.execute(
        update(QRAccessGrant)
        .where(
            QRAccessGrant.id == grant.id,
            QRAccessGrant.status == "issued",
            QRAccessGrant.expires_at > now,
            QRAccessGrant.redeemed_at.is_(None),
        )
        .values(status="redeeming", redeemed_at=now)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    if claim.rowcount != 1:
        db.refresh(grant)
        expiry = grant.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= now:
            raise HTTPException(status_code=410, detail="QR authorization has expired. Please scan the current station QR.")
        raise HTTPException(status_code=409, detail="QR authorization has already been used or is being processed.")

    device = db.get(Device, grant.device_id)
    if device is None:
        grant.status = "failed"
        grant.failure_reason = "Registered controller no longer exists."
        db.commit()
        raise HTTPException(status_code=404, detail="Registered controller not found.")

    try:
        result = sessions.open_door(device, door_index=grant.door_index, operator_id="CUSTOMER_QR")
    except (SDKUnavailableError, DeviceLoginError, ValueError) as exc:
        grant.status = "failed"
        grant.completed_at = datetime.now(timezone.utc)
        grant.failure_reason = str(exc)[:500]
        record_remote_unlock_event(
            db, device=device, door_index=grant.door_index, user_type="CUSTOMER",
            operator_id="CUSTOMER_QR", reason="QR_TEMP_ACCESS", command_status="failed", error=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Door controller rejected the unlock request: {exc}") from exc
    except Exception as exc:
        grant.status = "failed"
        grant.completed_at = datetime.now(timezone.utc)
        grant.failure_reason = str(exc)[:500]
        record_remote_unlock_event(
            db, device=device, door_index=grant.door_index, user_type="CUSTOMER",
            operator_id="CUSTOMER_QR", reason="QR_TEMP_ACCESS", command_status="failed", error=str(exc),
        )
        raise HTTPException(status_code=502, detail="Unexpected error while communicating with the door controller.") from exc

    grant.status = "used"
    grant.completed_at = datetime.now(timezone.utc)
    record = record_remote_unlock_event(
        db, device=device, door_index=grant.door_index, user_type="CUSTOMER",
        operator_id="CUSTOMER_QR", reason="QR_TEMP_ACCESS", command_status="command_accepted",
        sdk_result=result.get("sdk_result"),
    )
    return {
        "success": True,
        "status": "command_accepted",
        "event_id": record.id,
        "event_source": "REMOTE",
        "event_type": "REMOTE_UNLOCK",
        "user_type": "CUSTOMER",
        "device_id": device.id,
        "station_id": grant.station_id,
        "door_index": grant.door_index,
        "sdk_command": result.get("sdk_command"),
        "sdk_result": result.get("sdk_result"),
        "physical_door_state_verified": False,
        "message": "The controller accepted the one-time customer remote-unlock command.",
    }
