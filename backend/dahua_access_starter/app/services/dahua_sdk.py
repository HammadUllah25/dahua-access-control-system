from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any


class SDKUnavailableError(RuntimeError):
    pass


class DeviceLoginError(RuntimeError):
    pass


@dataclass
class LoginResult:
    handle: int
    serial_number: str | None
    device_info: Any = None


class DahuaSDK:
    """Small adapter for the Dahua NetSDK Python wheel already installed by you.

    This adapter deliberately implements initialization, login and logout first.
    Card and configuration operations will be added only after the installed
    wheel's exact structures/enums have been inspected on your Windows machine.
    """

    def __init__(self) -> None:
        self._client = None
        self._initialized = False
        self._lock = threading.RLock()
        self._import_error: str | None = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            try:
                from NetSDK.NetSDK import NetClient
            except Exception as exc:
                self._import_error = f"Could not import Dahua NetSDK: {exc}"
                raise SDKUnavailableError(self._import_error) from exc

            self._client = NetClient()
            try:
                ok = self._client.InitEx(None)
            except Exception as exc:
                self._client = None
                raise SDKUnavailableError(f"NetSDK InitEx failed: {exc}") from exc

            if not ok:
                self._client = None
                raise SDKUnavailableError("NetSDK InitEx returned failure.")
            self._initialized = True

    def login(self, host: str, port: int, username: str, password: str) -> LoginResult:
        self.initialize()
        try:
            from ctypes import sizeof
            from NetSDK.SDK_Enum import EM_LOGIN_SPAC_CAP_TYPE
            from NetSDK.SDK_Struct import (
                NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY,
                NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY,
            )

            login_in = NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY()
            login_in.dwSize = sizeof(NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY)
            login_in.szIP = host.encode("utf-8")
            login_in.nPort = int(port)
            login_in.szUserName = username.encode("utf-8")
            login_in.szPassword = password.encode("utf-8")
            login_in.emSpecCap = EM_LOGIN_SPAC_CAP_TYPE.TCP

            login_out = NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY()
            login_out.dwSize = sizeof(NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY)

            # This wrapper's documented Python pattern returns:
            # (login_handle, device_info, error_message).
            result = self._client.LoginWithHighLevelSecurity(login_in, login_out)
            if not isinstance(result, tuple) or len(result) < 3:
                raise DeviceLoginError(
                    "Unexpected LoginWithHighLevelSecurity return value. "
                    "Run tools/inspect_sdk.py and share its output."
                )

            raw_handle, device_info, error_message = result[0], result[1], result[2]
            handle = int(getattr(raw_handle, "value", raw_handle) or 0)
            if handle == 0:
                message = str(error_message or "Device login failed.")
                raise DeviceLoginError(message)

            serial = self._read_serial(login_out, device_info)
            return LoginResult(handle=handle, serial_number=serial, device_info=device_info)
        except (SDKUnavailableError, DeviceLoginError):
            raise
        except Exception as exc:
            raise DeviceLoginError(f"NetSDK login error: {exc}") from exc

    @staticmethod
    def _read_serial(login_out: Any, device_info: Any) -> str | None:
        candidates = [
            getattr(getattr(login_out, "stuDeviceInfo", None), "sSerialNumber", None),
            getattr(device_info, "sSerialNumber", None),
        ]
        for raw in candidates:
            if raw is None:
                continue
            try:
                if isinstance(raw, str):
                    value = raw
                else:
                    value = bytes(raw).split(b"\x00", 1)[0].decode("utf-8", "replace")
                value = value.strip()
                if value:
                    return value
            except Exception:
                continue
        return None

    def logout(self, handle: int) -> None:
        if not self._initialized or self._client is None or not handle:
            return
        try:
            self._client.Logout(handle)
        except Exception:
            # Continue shutdown even if a device has already disconnected.
            pass

    def cleanup(self) -> None:
        with self._lock:
            if self._initialized and self._client is not None:
                try:
                    self._client.Cleanup()
                finally:
                    self._initialized = False
                    self._client = None
