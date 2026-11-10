from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonCreate(BaseModel):
    person_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)

    @field_validator("person_code", "name")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("department", "phone", "email")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value.lower() if value and "@" in value else (value or None)


class PersonUpdate(BaseModel):
    person_code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)

    @field_validator("person_code", "name")
    @classmethod
    def trim_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("department", "phone", "email")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        return value.lower() if "@" in value else value


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_code: str
    name: str
    department: str | None
    phone: str | None
    email: str | None
    profile_source: str = "application"
    source_device_id: int | None = None
    created_at: datetime
    updated_at: datetime
