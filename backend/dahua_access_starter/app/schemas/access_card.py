from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AccessCardCreate(BaseModel):
    person_id: int = Field(gt=0)
    # Store the UID as text, not an integer, so leading zeroes are preserved.
    # Current card UIDs are entered as hexadecimal (e.g. FB66983B).
    card_number: str = Field(min_length=4, max_length=32, pattern=r"^(?:[0-9A-Fa-f]{2}){2,16}$")
    card_name: str | None = Field(default=None, max_length=64)
    card_type: Literal["general", "vip", "guest"] = "general"
    is_valid: bool = True
    valid_from: date = Field(default_factory=date.today)
    valid_until: date = date(2037, 12, 31)
    # ASI1201E Door 1 is typically index 0; use explicit indexes for other doors.
    door_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)
    # Schedule indexes are device configuration indexes, not hours/minutes.
    time_section_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=32)

    @field_validator("card_number")
    @classmethod
    def normalize_card_number(cls, value: str) -> str:
        return value.strip().upper()

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
        if any(i < 0 or i > 31 for i in self.door_indices):
            raise ValueError("door_indices must be between 0 and 31")
        if any(i < 0 or i > 31 for i in self.time_section_indices):
            raise ValueError("time_section_indices must be between 0 and 31")
        if len(set(self.door_indices)) != len(self.door_indices):
            raise ValueError("door_indices must not contain duplicates")
        if len(set(self.time_section_indices)) != len(self.time_section_indices):
            raise ValueError("time_section_indices must not contain duplicates")
        return self


class AccessCardUpdate(BaseModel):
    card_number: str | None = Field(default=None, min_length=4, max_length=32, pattern=r"^(?:[0-9A-Fa-f]{2}){2,16}$")
    card_name: str | None = Field(default=None, min_length=1, max_length=64)
    card_type: Literal["general", "vip", "guest"] | None = None
    is_valid: bool | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    door_indices: list[int] | None = Field(default=None, min_length=1, max_length=32)
    time_section_indices: list[int] | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("card_number")
    @classmethod
    def normalize_card_number(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("card_name")
    @classmethod
    def normalize_card_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("card_name cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must be on or after valid_from")
        for field_name in ("door_indices", "time_section_indices"):
            values = getattr(self, field_name)
            if values is not None:
                if any(i < 0 or i > 31 for i in values):
                    raise ValueError(f"{field_name} must be between 0 and 31")
                if not values or len(set(values)) != len(values):
                    raise ValueError(f"{field_name} must be non-empty and contain no duplicates")
        return self


class AccessCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    device_id: int
    card_number: str
    card_name: str
    device_record_no: int | None
    card_type: int
    device_card_status: int = 0
    is_valid: bool
    valid_from: date | None
    valid_until: date | None
    door_indices: list[int]
    time_section_indices: list[int]
    sync_status: str
    last_sync_error: str | None
    last_synced_at: datetime | None


class DevicePersonProfileRead(BaseModel):
    """Safe personnel fields returned by Dahua's access-user service.

    Credential secrets and raw biometric payloads are deliberately omitted.
    """
    user_id: str
    name: str | None = None
    name_source: str | None = None
    name_extension_enabled: bool = False
    user_type: int
    user_type_label: str
    user_status: int
    user_status_label: str
    times_used_limit: int | None = None
    times_used_label: str | None = None
    password_configured: bool = False
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    door_indices: list[int] = Field(default_factory=list)
    time_section_indices: list[int] = Field(default_factory=list)
    special_day_schedule_indices: list[int] = Field(default_factory=list)
    department: str | None = None
    phone_number: str | None = None
    sex_code: int | None = None
    birthday: date | None = None
    update_time: datetime | None = None
    has_citizen_id: bool = False
    floor_numbers: str | None = None
    room_numbers: str | None = None
    class_info: str | None = None
    student_number: str | None = None
    work_class: str | None = None
    custom_user_type: int | None = None
    custom_user_type_value: int | None = None
    fail_code: int | None = None


class DeviceCardRecordRead(BaseModel):
    record_number: int
    card_number: str
    card_name: str
    card_status: int
    card_type: int
    is_valid: bool
    person_status: bool = False
    valid_from: date | None
    valid_until: date | None
    card_created_at: datetime | None = None
    door_indices: list[int]
    time_section_indices: list[int]
    device_user_id: str | None = None
    password_configured: bool = False
    times_used_limit: int | None = None
    first_enter: bool = False
    handicap_card: bool = False
    face_template_count: int = 0
    device_user_type: int | None = None
    department_name: str | None = None
    company_name: str | None = None
    department_id: int | None = None
    sex_code: int | None = None
    role: str | None = None
    phone_number: str | None = None
    photo_path: str | None = None
    picture_id: str | None = None
    project_number: str | None = None
    project_name: str | None = None
    worker_type_id: str | None = None
    worker_type_name: str | None = None
    person_profile: DevicePersonProfileRead | None = None
    person_profile_error: str | None = None
