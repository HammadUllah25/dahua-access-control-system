from __future__ import annotations

import hmac
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.device import Device
from app.services.dahua_sdk import DeviceLoginError, SDKUnavailableError
from app.services.device_sessions import sessions
from app.services.remote_access_events import record_remote_unlock_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["Remote Door Control"])


class RemoteUnlockRequest(BaseModel):
    """Parameters for a single remote open command."""

    model_config = ConfigDict(extra="forbid")

    door_index: int = Field(default=0, ge=0, le=255, description="Zero-based Dahua door/channel index.")
    operator_id: str = Field(default="ACCESS_API", min_length=1, max_length=35)
    reason: str = Field(default="MANUAL", min_length=1, max_length=80)


def _authorize_unlock(x_unlock_api_key: str | None) -> None:
    configured_key = os.getenv("REMOTE_UNLOCK_API_KEY", "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Remote unlock is disabled. Configure REMOTE_UNLOCK_API_KEY in the "
                "backend .env file and restart the API."
            ),
        )
    if not x_unlock_api_key or not hmac.compare_digest(x_unlock_api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-Unlock-API-Key header is required.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


@router.post("/{device_id}/remote-unlock")
def remote_unlock_device(
    device_id: int,
    payload: RemoteUnlockRequest,
    db: Session = Depends(get_db),
    x_unlock_api_key: str | None = Header(default=None, alias="X-Unlock-API-Key"),
):
    """Send a protected remote-open command to a registered Dahua controller.

    A successful response confirms SDK command acceptance, not independent
    physical door-position verification. Payment providers must be verified
    server-to-server before application code invokes this operation.
    """
    _authorize_unlock(x_unlock_api_key)

    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    try:
        result = sessions.open_door(
            device,
            door_index=payload.door_index,
            operator_id=payload.operator_id,
        )
    except (SDKUnavailableError, DeviceLoginError) as exc:
        record = record_remote_unlock_event(
            db, device=device, door_index=payload.door_index, user_type="ADMIN",
            operator_id=payload.operator_id, reason=payload.reason, command_status="failed", error=str(exc),
        )
        logger.warning(
            "Remote unlock failed | device_id=%s | door_index=%s | reason=%s | error=%s",
            device_id, payload.door_index, payload.reason, exc,
        )
        raise HTTPException(status_code=502, detail={"message": str(exc), "event_id": record.id}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected remote unlock failure | device_id=%s", device_id)
        record = record_remote_unlock_event(
            db, device=device, door_index=payload.door_index, user_type="ADMIN",
            operator_id=payload.operator_id, reason=payload.reason, command_status="failed", error=str(exc),
        )
        raise HTTPException(
            status_code=502,
            detail={"message": f"Unexpected error while sending remote unlock command: {exc}", "event_id": record.id},
        ) from exc

    issued_at = datetime.now(timezone.utc).isoformat()
    event = record_remote_unlock_event(
        db, device=device, door_index=payload.door_index, user_type="ADMIN",
        operator_id=payload.operator_id, reason=payload.reason, command_status="command_accepted",
        sdk_result=result.get("sdk_result"),
    )
    logger.info(
        "Remote unlock command accepted | device_id=%s | door_index=%s | operator_id=%s | reason=%s",
        device_id,
        payload.door_index,
        payload.operator_id,
        payload.reason,
    )

    return {
        "success": True,
        "status": "command_accepted",
        "event_id": event.id,
        "event_source": "REMOTE",
        "event_type": "REMOTE_UNLOCK",
        "user_type": "ADMIN",
        "device_id": device_id,
        "device_name": device.name,
        "door_index": payload.door_index,
        "command": "REMOTE_OPEN",
        "sdk_command": result["sdk_command"],
        "sdk_result": result["sdk_result"],
        "operator_id": payload.operator_id,
        "reason": payload.reason,
        "command_issued_at": issued_at,
        "physical_door_state_verified": False,
        "message": (
            "The Dahua controller accepted the remote-open command. "
            "Physical door movement must be verified separately through a door sensor or access event."
        ),
    }
