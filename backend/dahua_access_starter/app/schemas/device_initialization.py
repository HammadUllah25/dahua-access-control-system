from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LocalInterfaceRead(BaseModel):
    ip_address: str


class DeviceDiscoveryRequest(BaseModel):
    local_ip: str | None = Field(
        default=None,
        description="Optional IPv4 address of the PC network adapter connected to the controller LAN.",
    )
    wait_seconds: int = Field(default=5, ge=2, le=15)


class DiscoveredDeviceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ip_address: str
    tcp_port: int
    http_port: int | None = None
    mac_address: str
    serial_number: str | None = None
    model: str | None = None
    device_type: str | None = None
    subnet_mask: str | None = None
    gateway: str | None = None
    local_ip: str
    init_status_raw: int
    initialization_state: str
    password_reset_flags: int
    supports_phone_reset: bool
    supports_email_reset: bool


class DeviceDiscoveryResponse(BaseModel):
    count: int
    searched_local_ips: list[str]
    wait_seconds: int
    devices: list[DiscoveredDeviceRead]


class DeviceInitializeRequest(BaseModel):
    mac_address: str = Field(min_length=1, max_length=39)
    local_ip: str = Field(min_length=7, max_length=15)
    username: str = Field(min_length=1, max_length=127)
    password: str = Field(min_length=1, max_length=127)
    confirm_password: str = Field(min_length=1, max_length=127)
    cellphone: str | None = Field(default=None, max_length=31)
    email: str | None = Field(default=None, max_length=63)


class DeviceInitializeResponse(BaseModel):
    success: bool
    message: str
    mac_address: str
    local_ip: str
    device_ip: str
    tcp_port: int
    serial_number: str | None = None
    model: str | None = None
    next_step: str
