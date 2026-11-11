from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AccessEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    device_name: str | None
    device_host: str | None
    device_serial_number: str | None
    alarm_type: int
    event_id: int | None
    sequence: int | None
    door_number: int | None
    door_name: str | None
    card_number: str | None
    user_id: str | None
    cardholder_name: str | None
    reader_id: str | None
    event_direction: str
    event_type_code: int | None
    open_method: int | None
    card_type: int | None
    access_result: str
    raw_status_code: int | None
    raw_em_status_code: int | None
    error_code: int | None
    device_event_time: datetime | None
    event_time_utc: datetime | None
    received_at: datetime
    raw_payload: dict
