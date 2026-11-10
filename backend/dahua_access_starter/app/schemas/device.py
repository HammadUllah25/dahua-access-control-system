from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    connection_type: str = Field(default="ip_domain", pattern="^(ip_domain)$")
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=37777, ge=1, le=65535)
    username: str = Field(default="admin", min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)
    model: str | None = Field(default="ASI1201E", max_length=80)
    connect_now: bool = True
    monitoring_enabled: bool = True


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, min_length=1, max_length=80)
    password: str | None = Field(default=None, min_length=1, max_length=256)
    model: str | None = Field(default=None, max_length=80)
    reconnect: bool = False
    monitoring_enabled: bool | None = None


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    connection_type: str
    host: str
    port: int
    username: str
    model: str | None
    serial_number: str | None
    status: str
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    last_connected_at: datetime | None
    monitoring_enabled: bool
    last_health_check_at: datetime | None
    last_tcp_reachable_at: datetime | None
    last_connect_attempt_at: datetime | None
    consecutive_failures: int
