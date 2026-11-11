from __future__ import annotations

import ipaddress
import threading
import time
from dataclasses import dataclass
from typing import Any

from app.services.network_interfaces import get_ethernet_ipv4_addresses


class DeviceDiscoveryError(RuntimeError):
    pass


class DeviceInitializationError(RuntimeError):
    pass


def _decode(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.split("\x00", 1)[0].strip()
    try:
        return bytes(value).split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
    except Exception:
        return str(value).strip()


def _normalise_mac(value: str) -> str:
    return value.strip().upper()


def get_local_ipv4_addresses() -> list[str]:
    """Return active Ethernet/LAN IPv4 addresses, excluding loopback and link-local."""
    return get_ethernet_ipv4_addresses()


@dataclass(frozen=True)
class DiscoveryRecord:
    data: dict[str, Any]
    discovered_at: float


class DeviceInitializationService:
    """NetSDK LAN discovery and first-time account initialization.

    The shared DahuaSDK adapter is injected so this service reuses the same
    singleton NetClient and SDK InitEx lifecycle as device sessions.
    """

    CACHE_TTL_SECONDS = 300

    def __init__(self, sdk_adapter) -> None:
        self._sdk_adapter = sdk_adapter
        self._lock = threading.RLock()
        self._discovered: dict[tuple[str, str], DiscoveryRecord] = {}

    @staticmethod
    def interfaces() -> list[dict[str, str]]:
        return [{"ip_address": ip} for ip in get_local_ipv4_addresses()]

    def discover(self, local_ip: str | None = None, wait_seconds: int = 5) -> dict[str, Any]:
        if not 2 <= int(wait_seconds) <= 15:
            raise DeviceDiscoveryError("wait_seconds must be between 2 and 15.")

        if local_ip:
            try:
                parsed = ipaddress.IPv4Address(local_ip)
            except ipaddress.AddressValueError as exc:
                raise DeviceDiscoveryError("local_ip must be a valid IPv4 address.") from exc
            if parsed.is_loopback or parsed.is_link_local or parsed.is_unspecified:
                raise DeviceDiscoveryError("Use the active IPv4 address of the adapter connected to the device LAN.")
            local_ips = [str(parsed)]
        else:
            local_ips = get_local_ipv4_addresses()

        if not local_ips:
            raise DeviceDiscoveryError(
                "No active Ethernet IPv4 adapter was detected. Supply local_ip explicitly, "
                "for example the laptop Ethernet address on the controller LAN."
            )

        with self._lock:
            self._sdk_adapter.initialize()
            client = self._sdk_adapter.client
            try:
                from ctypes import sizeof
                from NetSDK.SDK_Callback import fSearchDevicesCBEx
                from NetSDK.SDK_Enum import EM_SEND_SEARCH_TYPE
                from NetSDK.SDK_Struct import (
                    DEVICE_NET_INFO_EX2,
                    NET_IN_STARTSERACH_DEVICE,
                    NET_OUT_STARTSERACH_DEVICE,
                )
            except Exception as exc:
                raise DeviceDiscoveryError(f"Could not import discovery definitions from NetSDK: {exc}") from exc

            found: dict[tuple[str, str], dict[str, Any]] = {}
            callback_errors: list[str] = []
            handle_local_ips: dict[int, str] = {}
            data_lock = threading.Lock()

            def on_device(search_handle, device_pointer, user_data):
                try:
                    wrapper = device_pointer.contents
                    info = wrapper.stuDevInfo
                    if int(info.iIPVersion) != 4:
                        return

                    mac = _decode(info.szMac)
                    if not mac:
                        return
                    actual_local_ip = _decode(wrapper.szLocalIP)
                    if not actual_local_ip:
                        raw_handle = getattr(search_handle, "value", search_handle)
                        actual_local_ip = handle_local_ips.get(int(raw_handle or 0), "")
                    if not actual_local_ip and len(local_ips) == 1:
                        actual_local_ip = local_ips[0]
                    if not actual_local_ip:
                        raise ValueError("Search callback did not provide the local interface IP.")

                    raw_status = int(info.byInitStatus)
                    status_bits = raw_status & 0x03
                    if status_bits == 1:
                        state = "uninitialized"
                    elif status_bits == 2:
                        state = "initialized"
                    else:
                        state = "unsupported_or_legacy"

                    reset_flags = int(info.byPwdResetWay)
                    item = {
                        "ip_address": _decode(info.szIP),
                        "tcp_port": int(info.nPort),
                        "http_port": int(info.nHttpPort) or None,
                        "mac_address": mac,
                        "serial_number": _decode(info.szSerialNo) or None,
                        "model": _decode(info.szDetailType) or _decode(info.szNewDetailType) or None,
                        "device_type": _decode(info.szDeviceType) or None,
                        "subnet_mask": _decode(info.szSubmask) or None,
                        "gateway": _decode(info.szGateway) or None,
                        "local_ip": actual_local_ip,
                        "init_status_raw": raw_status,
                        "initialization_state": state,
                        "password_reset_flags": reset_flags,
                        "supports_phone_reset": bool(reset_flags & 0x01),
                        "supports_email_reset": bool(reset_flags & 0x02),
                    }
                    key = (_normalise_mac(mac), actual_local_ip)
                    with data_lock:
                        found[key] = item
                except Exception as exc:  # Never let Python exceptions cross a native callback boundary.
                    with data_lock:
                        callback_errors.append(str(exc))

            callback = fSearchDevicesCBEx(on_device)
            handles: list[int] = []
            start_errors: list[str] = []
            try:
                for interface_ip in local_ips:
                    search_in = NET_IN_STARTSERACH_DEVICE()
                    search_in.dwSize = sizeof(NET_IN_STARTSERACH_DEVICE)
                    search_in.szLocalIp = interface_ip.encode("ascii")
                    search_in.cbSearchDevices = callback
                    search_in.emSendType = EM_SEND_SEARCH_TYPE.MULTICAST_AND_BROADCAST

                    search_out = NET_OUT_STARTSERACH_DEVICE()
                    search_out.dwSize = sizeof(NET_OUT_STARTSERACH_DEVICE)
                    handle = client.StartSearchDevicesEx(search_in, search_out)
                    handle_value = int(getattr(handle, "value", handle) or 0)
                    if handle_value:
                        handles.append(handle_value)
                        handle_local_ips[handle_value] = interface_ip
                    else:
                        start_errors.append(
                            f"Search could not start on {interface_ip}: {client.GetLastErrorMessage()}"
                        )

                if not handles:
                    detail = "; ".join(start_errors) or "NetSDK returned no search handle."
                    raise DeviceDiscoveryError(detail)

                time.sleep(int(wait_seconds))
            finally:
                for handle in handles:
                    try:
                        client.StopSearchDevices(handle)
                    except Exception:
                        pass
                # Keep the callback object alive until every search handle is stopped.
                _ = callback

            with data_lock:
                result = sorted(found.values(), key=lambda row: (row["ip_address"], row["mac_address"]))

            now = time.monotonic()
            for key, record in list(self._discovered.items()):
                if now - record.discovered_at > self.CACHE_TTL_SECONDS:
                    self._discovered.pop(key, None)
            for item in result:
                cache_key = (_normalise_mac(item["mac_address"]), item["local_ip"])
                self._discovered[cache_key] = DiscoveryRecord(data=item, discovered_at=now)

            return {
                "count": len(result),
                "searched_local_ips": local_ips,
                "wait_seconds": int(wait_seconds),
                "devices": result,
            }

    def initialize_device(
        self,
        *,
        mac_address: str,
        local_ip: str,
        username: str,
        password: str,
        confirm_password: str,
        cellphone: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        if password != confirm_password:
            raise DeviceInitializationError("Password and confirm_password do not match.")
        if not username.strip() or not password:
            raise DeviceInitializationError("Username and password are required.")

        try:
            local_ip = str(ipaddress.IPv4Address(local_ip))
        except ipaddress.AddressValueError as exc:
            raise DeviceInitializationError("local_ip must be a valid IPv4 address.") from exc

        cache_key = (_normalise_mac(mac_address), local_ip)
        with self._lock:
            cached = self._discovered.get(cache_key)
            if cached is None or time.monotonic() - cached.discovered_at > self.CACHE_TTL_SECONDS:
                self._discovered.pop(cache_key, None)
                raise DeviceInitializationError(
                    "This device was not found in a recent discovery result. Run discovery again and use "
                    "the exact mac_address and local_ip returned for the device."
                )

            device = cached.data
            if device["initialization_state"] != "uninitialized":
                raise DeviceInitializationError(
                    f"The device is not reported as uninitialized (state: {device['initialization_state']})."
                )

            reset_flags = int(device["password_reset_flags"])
            if cellphone and not (reset_flags & 0x01):
                raise DeviceInitializationError("This device did not report support for cellphone password recovery.")
            if email and not (reset_flags & 0x02):
                raise DeviceInitializationError("This device did not report support for email password recovery.")

            for field_name, value, max_bytes in (
                ("mac_address", device["mac_address"], 39),
                ("username", username, 127),
                ("password", password, 127),
                ("cellphone", cellphone or "", 31),
                ("email", email or "", 63),
            ):
                if len(value.encode("utf-8")) > max_bytes:
                    raise DeviceInitializationError(f"{field_name} exceeds the NetSDK field byte limit ({max_bytes}).")

            self._sdk_adapter.initialize()
            client = self._sdk_adapter.client
            try:
                from ctypes import sizeof
                from NetSDK.SDK_Enum import EM_ACCOUNT_PROTOCOL
                from NetSDK.SDK_Struct import NET_IN_INIT_DEVICE_ACCOUNT, NET_OUT_INIT_DEVICE_ACCOUNT
            except Exception as exc:
                raise DeviceInitializationError(f"Could not import account initialization structures: {exc}") from exc

            init_in = NET_IN_INIT_DEVICE_ACCOUNT()
            init_in.dwSize = sizeof(NET_IN_INIT_DEVICE_ACCOUNT)
            init_in.szMac = device["mac_address"].encode("utf-8")
            init_in.szUserName = username.encode("utf-8")
            init_in.szPwd = password.encode("utf-8")
            if cellphone:
                init_in.szCellPhone = cellphone.encode("utf-8")
            if email:
                init_in.szMail = email.encode("utf-8")
            # The SDK explicitly requires the reset-method flags returned by the search callback.
            init_in.byPwdResetWay = reset_flags
            init_in.emAccountProtocol = EM_ACCOUNT_PROTOCOL.ACCOUNT_PROTOCOL_NORMAL
            init_in.bIs4th = False

            init_out = NET_OUT_INIT_DEVICE_ACCOUNT()
            init_out.dwSize = sizeof(NET_OUT_INIT_DEVICE_ACCOUNT)

            success = client.InitDevAccount(init_in, init_out, 8000, local_ip.encode("ascii"))
            if not success:
                error_code = client.GetLastError()
                error_message = client.GetLastErrorMessage()
                raise DeviceInitializationError(
                    f"Dahua InitDevAccount failed (SDK error {error_code}): {error_message}"
                )

            # This discovery record must not be reused for a second initialization attempt.
            self._discovered.pop(cache_key, None)

            return {
                "success": True,
                "message": "The device account was initialized successfully.",
                "mac_address": device["mac_address"],
                "local_ip": local_ip,
                "device_ip": device["ip_address"],
                "tcp_port": device["tcp_port"],
                "serial_number": device["serial_number"],
                "model": device["model"],
                "next_step": (
                    "Register this controller with POST /devices using the discovered device_ip, "
                    "tcp_port, and the new username/password."
                ),
            }


# Reuse the same SDK adapter/NetClient instance used by device sessions.
from app.services.device_sessions import sessions

initialization_service = DeviceInitializationService(sessions.sdk)
