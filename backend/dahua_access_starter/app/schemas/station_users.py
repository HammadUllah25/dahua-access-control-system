from __future__ import annotations

from datetime import date, datetime
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OperationalRoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    code: str | None = Field(default=None, min_length=2, max_length=20, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    description: str | None = Field(default=None, max_length=500)
    default_is_billable: bool = False

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role name cannot be blank")
        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class OperationalRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    default_is_billable: bool | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Role name cannot be blank")
        return value


class OperationalRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    station_id: int | None
    code: str
    name: str
    description: str | None
    is_system: bool
    default_is_billable: bool
    is_active: bool
    created_at: datetime


class StationUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    role_id: int = Field(gt=0)
    is_billable: bool | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("User name cannot be blank")
        return value

    @field_validator("phone")
    @classmethod
    def trim_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class StationUserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    role_id: int | None = Field(default=None, gt=0)
    is_billable: bool | None = None
    clear_billable_override: bool = False
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("User name cannot be blank")
        return value

    @field_validator("phone")
    @classmethod
    def trim_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_billable_fields(self):
        if self.clear_billable_override and self.is_billable is not None:
            raise ValueError("Provide is_billable or clear_billable_override, not both")
        return self


class UserAssignedCardRead(BaseModel):
    id: int
    station_card_assignment_id: int
    device_id: int
    card_number: str
    card_name: str
    sync_status: str
    is_valid: bool
    valid_from: date | None
    valid_until: date | None
    assigned_at: datetime


class StationUserRead(BaseModel):
    id: int
    station_id: int
    name: str
    phone: str | None
    role: OperationalRoleRead
    is_billable: bool
    is_billable_override: bool | None
    is_active: bool
    active_card: UserAssignedCardRead | None = None
    created_at: datetime
    updated_at: datetime


class StationUserCardEnrollmentStart(BaseModel):
    device_id: int = Field(gt=0)
    timeout_seconds: int = Field(default=90, ge=10, le=300)


class StationUserCardEnrollmentConfirm(BaseModel):
    card_name: str | None = Field(default=None, max_length=64)
    card_type: Literal["general", "vip", "guest"] = "general"
    is_valid: bool = True
    valid_from: date = Field(default_factory=date.today)
    valid_until: date = date(2037, 12, 31)
    door_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)
    time_section_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)

    @field_validator("card_name")
    @classmethod
    def trim_card_name(cls, value: str | None) -> str | None:
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


class AdoptStationCardRequest(BaseModel):
    station_card_assignment_id: int = Field(gt=0)


class UserCardAssignmentRead(BaseModel):
    id: int
    station_user_id: int
    station_card_assignment_id: int
    station_id: int
    device_id: int
    card_number: str
    is_active: bool
    assigned_at: datetime
    ended_at: datetime | None
