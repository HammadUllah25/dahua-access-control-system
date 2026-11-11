
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SDKUnavailableError(RuntimeError):
    pass


class DeviceLoginError(RuntimeError):
    pass


class DeviceSubscriptionError(RuntimeError):
    pass


@dataclass
class LoginResult:
    handle: int
    serial_number: str | None
    device_info: Any = None


class DahuaSDK:
    """Adapter for the installed Dahua NetSDK Python wrapper."""

    def __init__(self) -> None:
        self._client = None
        self._initialized = False
        self._lock = threading.RLock()
        self._import_error: str | None = None

        # Retain callbacks and subscription handles while subscriptions
        # are active. Native SDK callbacks must remain referenced.
        self._message_callback_ref: Any = None
        self._message_handlers: dict[int, Callable[[dict[str, Any]], None]] = {}
        self._access_event_command: int | None = None

    @property
    def available(self) -> bool:
        return self._client is not None and self._initialized

    @property
    def client(self):
        """Return the shared NetSDK client, initializing it if required."""
        self.initialize()
        return self._client

    @staticmethod
    def _as_int(value: Any) -> int:
        """Convert regular or ctypes scalar values to Python integers."""
        return int(getattr(value, "value", value) or 0)

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return

            try:
                from NetSDK.NetSDK import NetClient
            except Exception as exc:
                self._import_error = (
                    f"Could not import Dahua NetSDK: {exc}"
                )
                raise SDKUnavailableError(self._import_error) from exc

            self._client = NetClient()

            try:
                ok = self._client.InitEx(None)
            except Exception as exc:
                self._client = None
                raise SDKUnavailableError(
                    f"NetSDK InitEx failed: {exc}"
                ) from exc

            if not ok:
                self._client = None
                raise SDKUnavailableError(
                    "NetSDK InitEx returned failure."
                )

            try:
                from NetSDK import SDK_Callback
                from NetSDK.SDK_Enum import SDK_ALARM_TYPE

                self._access_event_command = int(SDK_ALARM_TYPE.ALARM_ACCESS_CTL_EVENT)
                self._message_callback_ref = SDK_Callback.fMessCallBackEx1(self._on_alarm_message)
                self._client.SetDVRMessCallBackEx1(self._message_callback_ref, 0)
            except Exception as exc:
                try:
                    self._client.Cleanup()
                finally:
                    self._client = None
                raise SDKUnavailableError(
                    f"Could not register the Dahua alarm message callback: {exc}"
                ) from exc

            self._initialized = True
            logger.info("Dahua NetSDK initialized and global alarm callback registered.")

    def login(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> LoginResult:
        self.initialize()

        try:
            from ctypes import sizeof
            from NetSDK.SDK_Enum import EM_LOGIN_SPAC_CAP_TYPE
            from NetSDK.SDK_Struct import (
                NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY,
                NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY,
            )

            login_in = NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY()
            login_in.dwSize = sizeof(
                NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY
            )
            login_in.szIP = host.encode("utf-8")
            login_in.nPort = int(port)
            login_in.szUserName = username.encode("utf-8")
            login_in.szPassword = password.encode("utf-8")
            login_in.emSpecCap = EM_LOGIN_SPAC_CAP_TYPE.TCP

            login_out = NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY()
            login_out.dwSize = sizeof(
                NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY
            )

            result = self._client.LoginWithHighLevelSecurity(
                login_in,
                login_out,
            )

            if not isinstance(result, tuple) or len(result) < 3:
                raise DeviceLoginError(
                    "Unexpected LoginWithHighLevelSecurity return value."
                )

            raw_handle, device_info, error_message = result[:3]
            handle = self._as_int(raw_handle)

            if handle == 0:
                raise DeviceLoginError(
                    str(error_message or "Device login failed.")
                )

            serial = self._read_serial(login_out, device_info)

            # Diagnostic information for subscription troubleshooting.
            channel_count = getattr(
                device_info,
                "nChanNum",
                "unavailable",
            )

            logger.info(
                "Dahua login details | "
                "host=%s | "
                "handle=%s | "
                "serial=%s | "
                "channel_count=%s",
                host,
                handle,
                serial,
                channel_count,
            )

            return LoginResult(
                handle=handle,
                serial_number=serial,
                device_info=device_info,
            )

        except (SDKUnavailableError, DeviceLoginError):
            raise
        except Exception as exc:
            raise DeviceLoginError(
                f"NetSDK login error: {exc}"
            ) from exc

    @staticmethod
    def _read_serial(
        login_out: Any,
        device_info: Any,
    ) -> str | None:
        candidates = [
            getattr(
                getattr(login_out, "stuDeviceInfo", None),
                "sSerialNumber",
                None,
            ),
            getattr(device_info, "sSerialNumber", None),
        ]

        for raw in candidates:
            if raw is None:
                continue

            try:
                if isinstance(raw, str):
                    value = raw
                else:
                    value = (
                        bytes(raw)
                        .split(b"\x00", 1)[0]
                        .decode("utf-8", "replace")
                    )

                value = value.strip()

                if value:
                    return value

            except Exception:
                continue

        return None

    @staticmethod
    def _read_c_string(value: Any) -> str | None:
        if value is None:
            return None
        try:
            if isinstance(value, str):
                result = value
            else:
                result = bytes(value).split(b"\x00", 1)[0].decode("utf-8", "replace")
            result = result.strip()
            return result or None
        except Exception:
            return None

    @staticmethod
    def _read_time(value: Any, *, utc: bool = False) -> str | None:
        """Decode a Dahua NET_TIME/NET_TIME_EX structure to ISO text."""
        if value is None:
            return None

        def component(*names: str) -> int | None:
            for name in names:
                raw = getattr(value, name, None)
                if raw is not None:
                    try:
                        return int(getattr(raw, "value", raw))
                    except (TypeError, ValueError):
                        pass
            return None

        parts = [
            component("dwYear", "year", "nYear"),
            component("dwMonth", "month", "nMonth"),
            component("dwDay", "day", "nDay"),
            component("dwHour", "hour", "nHour"),
            component("dwMinute", "minute", "nMinute"),
            component("dwSecond", "second", "nSecond"),
        ]
        if any(part is None for part in parts):
            return None
        try:
            dt = datetime(*parts)
            if utc:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError):
            return None

    @classmethod
    def _decode_alarm_access_event(cls, event: Any, alarm_type: int, event_id: int) -> dict[str, Any]:
        direction_code = cls._as_int(getattr(event, "emEventType", 0))
        direction = {0: "UNKNOWN", 1: "ENTRY", 2: "EXIT"}.get(direction_code, "OTHER")
        real_utc_flag = bool(cls._as_int(getattr(event, "bRealUTC", 0)))
        real_utc = getattr(event, "RealUTC", None) if real_utc_flag else None
        raw_status = cls._as_int(getattr(event, "bStatus", 0))
        return {
            "alarm_type": alarm_type,
            "event_id": cls._as_int(event_id),
            "sequence": None,
            "door_number": cls._as_int(getattr(event, "nDoor", 0)),
            "door_name": cls._read_c_string(getattr(event, "szDoorName", None)),
            "card_number": cls._read_c_string(getattr(event, "szCardNo", None)),
            "user_id": cls._read_c_string(getattr(event, "szUserID", None)),
            "cardholder_name": cls._read_c_string(getattr(event, "szCardName", None)),
            "reader_id": cls._read_c_string(getattr(event, "szReaderID", None)),
            "event_direction": direction,
            "event_type_code": direction_code,
            "open_method": cls._as_int(getattr(event, "emOpenMethod", 0)),
            "card_type": cls._as_int(getattr(event, "emCardType", 0)),
            # Dahua SDK structure documentation: bStatus TRUE=success, FALSE=failure.
            "access_result": "granted" if raw_status else "denied",
            "raw_status_code": raw_status,
            "raw_em_status_code": cls._as_int(getattr(event, "emStatus", 0)),
            "error_code": cls._as_int(getattr(event, "nErrorCode", 0)),
            "device_event_time": cls._read_time(getattr(event, "stuTime", None), utc=False),
            "event_time_utc": cls._read_time(real_utc, utc=True),
            "event_device_serial_number": cls._read_c_string(getattr(event, "szSN", None)),
            "real_utc_available": real_utc_flag,
        }

    def _on_alarm_message(
        self,
        command,
        login_id,
        buffer,
        buffer_length,
        device_ip,
        device_port,
        alarm_ack_flag,
        event_id,
        user_data,
    ) -> None:
        """Native NetSDK callback. Copy the payload and hand it to the app handler."""
        try:
            command_value = self._as_int(command)
            if command_value != self._access_event_command:
                return

            login_handle = self._as_int(login_id)
            with self._lock:
                handler = self._message_handlers.get(login_handle)
            if handler is None:
                return

            from ctypes import POINTER, cast, sizeof
            from NetSDK.SDK_Struct import NET_A_ALARM_ACCESS_CTL_EVENT_INFO

            required_size = sizeof(NET_A_ALARM_ACCESS_CTL_EVENT_INFO)
            received_size = self._as_int(buffer_length)
            if not buffer or received_size < required_size:
                logger.warning(
                    "Ignored malformed access event buffer | login_handle=%s | received=%s | required=%s",
                    login_handle, received_size, required_size,
                )
                return

            event_data = cast(
                buffer,
                POINTER(NET_A_ALARM_ACCESS_CTL_EVENT_INFO),
            ).contents
            payload = self._decode_alarm_access_event(
                event_data, command_value, self._as_int(event_id)
            )
            handler(payload)
        except Exception:
            # No exception may escape into the native SDK callback thread.
            logger.exception("Exception inside Dahua alarm message callback.")

    def subscribe_access_events(
        self,
        login_handle: int,
        on_event: Callable[[dict[str, Any]], None],
        channel_id: int = 0,
    ) -> int:
        """Subscribe using Dahua's SetDVRMessCallBackEx1 + StartListenEx flow."""
        self.initialize()
        login_handle = int(login_handle)
        with self._lock:
            if login_handle in self._message_handlers:
                return 1
            self._message_handlers[login_handle] = on_event
            try:
                result = self._client.StartListenEx(login_handle)
                success = bool(self._as_int(result))
                if not success:
                    try:
                        error_code = self._as_int(self._client.GetLastError())
                        error_message = self._client.GetLastErrorMessage()
                    except Exception:
                        error_code, error_message = -1, "Could not read SDK error."
                    self._message_handlers.pop(login_handle, None)
                    raise DeviceSubscriptionError(
                        f"StartListenEx failed (0x{error_code & 0xFFFFFFFF:08X}): {error_message}"
                    )
                logger.info(
                    "Dahua access alarm listening started | login_handle=%s | command=0x%04X",
                    login_handle, self._access_event_command or 0,
                )
                return 1
            except DeviceSubscriptionError:
                raise
            except Exception as exc:
                self._message_handlers.pop(login_handle, None)
                raise DeviceSubscriptionError(f"Could not start Dahua alarm listening: {exc}") from exc

    def stop_access_events(self, login_handle: int) -> bool:
        """Stop alarm listening for one login handle."""
        login_handle = int(login_handle)
        with self._lock:
            if login_handle not in self._message_handlers:
                return True
            try:
                stopped = bool(self._as_int(self._client.StopListen(login_handle)))
                if stopped:
                    self._message_handlers.pop(login_handle, None)
                    logger.info("Dahua alarm listening stopped | login_handle=%s", login_handle)
                else:
                    logger.warning(
                        "StopListen returned failure | login_handle=%s | error=%s",
                        login_handle, self._client.GetLastErrorMessage(),
                    )
                return stopped
            except Exception:
                logger.exception("Could not stop Dahua alarm listening | login_handle=%s", login_handle)
                return False

    def logout(self, handle: int) -> None:
        if not self._initialized or self._client is None or not handle:
            return
        try:
            self.stop_access_events(handle)
            self._client.Logout(handle)
        except Exception:
            logger.exception("Dahua logout failed | login_handle=%s", handle)

    def cleanup(self) -> None:
        with self._lock:
            if self._initialized and self._client is not None:
                for handle in list(self._message_handlers):
                    try:
                        self._client.StopListen(handle)
                    except Exception:
                        logger.exception("StopListen failed during SDK cleanup | login_handle=%s", handle)
                self._message_handlers.clear()
                try:
                    self._client.Cleanup()
                finally:
                    self._message_callback_ref = None
                    self._initialized = False
                    self._client = None
                    logger.info("Dahua NetSDK cleaned up.")
