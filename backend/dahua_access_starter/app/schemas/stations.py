from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Role = Literal["USER", "STAFF"]


class StationCreate(BaseModel):
    station_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=80)
    contact_name: str | None = Field(default=None, max_length=120)
    contact_phone: str | None = Field(default=None, max_length=40)
    is_active: bool = True

    @field_validator("station_code", "name")
    @classmethod
    def trim_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class StationUpdate(BaseModel):
    station_code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=80)
    contact_name: str | None = Field(default=None, max_length=120)
    contact_phone: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    station_code: str
    name: str
    address: str | None
    city: str | None
    contact_name: str | None
    contact_phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StationCardCreate(BaseModel):
    device_id: int = Field(gt=0)
    card_number: str = Field(min_length=4, max_length=32, pattern=r"^(?:[0-9A-Fa-f]{2}){2,16}$")
    role: Role = "USER"
    card_name: str | None = Field(default=None, max_length=64)
    is_billable: bool | None = None
    card_type: Literal["general", "vip", "guest"] = "general"
    is_valid: bool = True
    valid_from: date = Field(default_factory=date.today)
    valid_until: date = date(2037, 12, 31)
    door_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)
    time_section_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)

    @field_validator("card_number")
    @classmethod
    def normalize_uid(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_card(self):
        if self.valid_until < self.valid_from:
            raise ValueError("valid_until must be on or after valid_from")
        for field_name in ("door_indices", "time_section_indices"):
            values = getattr(self, field_name)
            if any(value < 0 or value > 31 for value in values):
                raise ValueError(f"{field_name} must be between 0 and 31")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class StationCardAdoptRequest(BaseModel):
    """Link an existing person-based card to a station role without re-enrolling it.

    The legacy AccessCard row remains intact for compatibility and history. The
    new station assignment is the cloud-owned record used for USER/STAFF
    reporting and post-reset reprovisioning.
    """

    device_id: int = Field(gt=0)
    card_number: str = Field(min_length=4, max_length=32, pattern=r"^(?:[0-9A-Fa-f]{2}){2,16}$")
    role: Role = "USER"
    card_name: str | None = Field(default=None, max_length=64)
    is_billable: bool | None = None

    @field_validator("card_number")
    @classmethod
    def normalize_uid(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.upper()

    @field_validator("card_name")
    @classmethod
    def trim_card_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("card_name cannot be blank")
        return value


class StationCardUpdate(BaseModel):
    role: Role | None = None
    card_name: str | None = Field(default=None, min_length=1, max_length=64)
    is_billable: bool | None = None
    is_active: bool | None = None
    is_valid: bool | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    card_type: Literal["general", "vip", "guest"] | None = None
    door_indices: list[int] | None = Field(default=None, min_length=1, max_length=32)
    time_section_indices: list[int] | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @model_validator(mode="after")
    def validate_card(self):
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must be on or after valid_from")
        for field_name in ("door_indices", "time_section_indices"):
            values = getattr(self, field_name)
            if values is not None and (not values or len(values) != len(set(values)) or any(v < 0 or v > 31 for v in values)):
                raise ValueError(f"{field_name} must contain unique indexes between 0 and 31")
        return self


class StationCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    station_id: int
    device_id: int
    card_number: str
    card_name: str
    role: str
    is_billable: bool
    is_active: bool
    device_record_no: int | None
    card_type: int
    device_card_status: int
    is_valid: bool
    valid_from: date | None
    valid_until: date | None
    door_indices: list[int]
    time_section_indices: list[int]
    sync_status: str
    last_sync_error: str | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
    station_user_id: int | None = None
    station_user_name: str | None = None
    operational_role_code: str | None = None
    operational_role_name: str | None = None




class DatabaseOnlyStationCardDeleteRequest(BaseModel):
    assignment_ids: list[int] = Field(min_length=1, max_length=500)
    confirmation: Literal["DELETE_DATABASE_ONLY"]

    @field_validator("assignment_ids")
    @classmethod
    def validate_assignment_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value):
            raise ValueError("assignment_ids must contain positive IDs")
        if len(value) != len(set(value)):
            raise ValueError("assignment_ids must not contain duplicates")
        return value


class StationRateCreate(BaseModel):
    role: Role
    rate_per_use: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="PKR", min_length=3, max_length=3)
    effective_from: date
    effective_until: date | None = None

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.upper()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "PKR":
            raise ValueError("This deployment currently supports PKR accounting only")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("effective_until must be on or after effective_from")
        return self


class StationRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    station_id: int
    role: str
    rate_per_use: Decimal
    currency: str
    effective_from: date
    effective_until: date | None
    created_at: datetime


class CashCollectionCreate(BaseModel):
    period_start: date
    period_end: date
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="PKR", min_length=3, max_length=3)
    collected_at: datetime | None = None
    received_by: str = Field(min_length=1, max_length=120)
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "PKR":
            raise ValueError("This deployment currently supports PKR accounting only")
        return value

    @field_validator("received_by")
    @classmethod
    def normalize_received_by(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("received_by cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class CashCollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    station_id: int
    period_start: date
    period_end: date
    amount: Decimal
    currency: str
    collected_at: datetime
    received_by: str
    reference: str | None
    notes: str | None
    created_at: datetime


class ReprovisionRequest(BaseModel):
    confirmation: str = Field(pattern=r"^REPROVISION_FROM_CLOUD$")
    controller_confirmed_factory_reset: bool = False


class ManualReprovisionVerificationRequest(BaseModel):
    """Manual confirmation for devices whose firmware cannot read card inventory."""

    confirmation: str = Field(pattern=r"^I_VERIFIED_EACH_CARD_IN_SMARTPSS_AND_TESTED_ACCESS$")
    verified_card_numbers: list[str] = Field(min_length=1, max_length=250)

    @field_validator("verified_card_numbers")
    @classmethod
    def normalize_verified_numbers(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values]
        if any(not re.fullmatch(r"(?:[0-9A-F]{2}){2,16}", value) for value in normalized):
            raise ValueError("Every card number must be a hexadecimal RFID UID between 4 and 32 characters")
        if len(normalized) != len(set(normalized)):
            raise ValueError("verified_card_numbers must not contain duplicates")
        return normalized


class InventoryCheckRead(BaseModel):
    device_id: int
    station_id: int | None
    inventory_status: str
    expected_count: int
    observed_count: int
    missing_cards: list[str]
    unexpected_cards: list[str]
    sync_job_id: int
    reprovision_job_id: int | None = None
    note: str
