from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.schemas.access_card import AccessCardRead


class CardEnrollmentStart(BaseModel):
    timeout_seconds: int = Field(default=90, ge=10, le=300)


class CardEnrollmentRead(BaseModel):
    session_token: str
    device_id: int
    status: Literal["waiting", "captured", "confirming", "confirmed", "expired", "cancelled"]
    card_number: str | None = None
    created_at: datetime
    expires_at: datetime
    captured_at: datetime | None = None
    event_access_result: str | None = None
    event_error_code: int | None = None
    event_door_number: int | None = None
    message: str


class CardEnrollmentConfirm(BaseModel):
    person_id: int = Field(gt=0)
    # This is the Dahua personnel credential password for UserID + password mode.
    # It is sent to the controller and is never stored in the application's database.
    user_password: SecretStr | None = Field(default=None, min_length=1, max_length=63)
    card_name: str | None = Field(default=None, max_length=64)
    card_type: Literal["general", "vip", "guest"] = "general"
    is_valid: bool = True
    valid_from: date = Field(default_factory=date.today)
    valid_until: date = date(2037, 12, 31)
    door_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)
    time_section_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)

    @field_validator("user_password")
    @classmethod
    def validate_password_bytes(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value().encode("utf-8")) > 63:
            raise ValueError("user_password must not exceed 63 UTF-8 bytes")
        return value

    @field_validator("card_name")
    @classmethod
    def normalize_card_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_dates_and_indexes(self):
        if self.valid_until < self.valid_from:
            raise ValueError("valid_until must be on or after valid_from")
        for field_name in ("door_indices", "time_section_indices"):
            values = getattr(self, field_name)
            if any(value < 0 or value > 31 for value in values):
                raise ValueError(f"{field_name} must be between 0 and 31")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class CardEnrollmentConfirmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    device_user_id: str
    card: AccessCardRead
