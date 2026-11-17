
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

    def get_new_dev_config_text(
        self, login_handle: int, command: str, channel: int = 0, buffer_size: int = 262144
    ) -> str:
        """Read a Dahua generic configuration payload without modifying the device."""
        from ctypes import c_char, sizeof

        if not login_handle:
            raise DeviceLoginError("A valid Dahua login handle is required.")
        if not command or len(command) > 64:
            raise ValueError("A valid Dahua configuration command is required.")
        if not 4096 <= buffer_size <= 2_097_152:
            raise ValueError("Configuration buffer size is outside the allowed range.")

        with self._lock:
            client = self.client
            out_buffer = (c_char * buffer_size)()
            ok = client.GetNewDevConfig(
                login_handle, command, int(channel), out_buffer, sizeof(out_buffer), 0, 5000
            )
            if not ok:
                raise DeviceLoginError(
                    f"GetNewDevConfig({command}, channel={channel}) failed: "
                    f"{client.GetLastErrorMessage()}"
                )
            raw = bytes(out_buffer).rstrip(b"\x00")
            if not raw:
                raise DeviceLoginError(
                    f"Dahua returned an empty {command} configuration response."
                )
            return raw.decode("utf-8", errors="replace").strip()

    def set_new_dev_config_text(
        self,
        login_handle: int,
        command: str,
        channel: int,
        body: str,
        *,
        restart: bool = False,
        waittime: int = 5000,
    ) -> None:
        """Write a Dahua generic configuration JSON payload through NetSDK."""
        from ctypes import create_string_buffer

        if not login_handle:
            raise DeviceLoginError("A valid Dahua login handle is required.")
        if not command or len(command) > 64:
            raise ValueError("A valid Dahua configuration command is required.")
        if not isinstance(body, str) or not body.strip():
            raise ValueError("A non-empty Dahua configuration JSON payload is required.")

        encoded = body.encode("utf-8")
        # The NetSDK wrapper expects a ctypes character buffer and the payload
        # length excluding the trailing NUL byte. Keep the buffer alive for the
        # duration of the native call.
        in_buffer = create_string_buffer(encoded, len(encoded) + 1)

        with self._lock:
            client = self.client
            ok = client.SetNewDevConfig(
                login_handle,
                command,
                int(channel),
                in_buffer,
                len(encoded),
                0,
                int(restart),
                int(waittime),
            )
            if not ok:
                try:
                    error_message = client.GetLastErrorMessage()
                except Exception:
                    error_message = "Could not read the NetSDK error message."
                raise DeviceLoginError(
                    f"SetNewDevConfig({command}, channel={channel}) failed: {error_message}"
                )

    def set_access_control_config_fields(
        self,
        login_handle: int,
        channel: int,
        body: str,
        changes: dict[str, bool | int],
        expected_current_entry: dict[str, Any],
        *,
        waittime: int = 5000,
    ) -> dict[str, Any]:
        """Read/modify/packet/write supported Dahua AccessControl fields safely.

        The raw JSON returned by GetNewDevConfig must be parsed to Dahua's
        native structure before PacketData and SetNewDevConfig are called.
        A strict ParseData returned-size check prevents writes when the local
        ctypes layout does not match the installed NetSDK runtime.
        """
        from ctypes import (
            POINTER,
            byref,
            c_char_p,
            c_int,
            c_uint32,
            cast,
            create_string_buffer,
            sizeof,
            c_void_p,
        )

        from .dahua_access_control_structs import (
            CFG_ACCESS_EVENT_INFO,
            CFG_ACCESS_EVENT_INFO_EXPECTED_SIZE,
        )

        if not login_handle:
            raise DeviceLoginError("A valid Dahua login handle is required.")
        if channel < 0:
            raise ValueError("AccessControl channel must be zero or greater.")
        if not isinstance(body, str) or not body.strip():
            raise ValueError("A non-empty AccessControl JSON response is required.")
        if not changes:
            raise ValueError("At least one AccessControl field update is required.")

        # Keep this allow-list deliberately narrow. Each JSON key is cross-
        # checked against the parsed native structure before any write occurs.
        native_field_map = {
            "SensorEnable": "bSensorEnable",
            "CloseCheckSensor": "bCloseCheckSensor",
            "CloseTimeout": "nCloseTimeout",
            "DoorNotClosedAlarmEnable": "bDoorNotClosedAlarmEnable",
            "BreakInAlarmEnable": "bBreakInAlarmEnable",
            "DuressAlarmEnable": "bDuressAlarmEnable",
            "UnlockHoldInterval": "nUnlockHoldInterval",
        }
        unsupported_fields = set(changes) - set(native_field_map)
        if unsupported_fields:
            raise ValueError(
                "Unsupported native AccessControl field(s): "
                f"{sorted(unsupported_fields)}."
            )
        missing_current = set(changes) - set(expected_current_entry)
        if missing_current:
            raise DeviceLoginError(
                "The controller's current AccessControl response does not expose "
                f"{sorted(missing_current)}. No device write was attempted."
            )

        structure_size = sizeof(CFG_ACCESS_EVENT_INFO)
        if structure_size != CFG_ACCESS_EVENT_INFO_EXPECTED_SIZE:
            raise DeviceLoginError(
                "Local CFG_ACCESS_EVENT_INFO layout is invalid: "
                f"size={structure_size}, expected={CFG_ACCESS_EVENT_INFO_EXPECTED_SIZE}. "
                "No device write was attempted."
            )

        encoded_body = body.encode("utf-8")
        input_json = create_string_buffer(encoded_body, len(encoded_body) + 1)
        command = b"AccessControl"  # Dahua CFG_CMD_ACCESS_EVENT
        access_info = CFG_ACCESS_EVENT_INFO()
        parsed_size = c_uint32(0)

        with self._lock:
            client = self.client
            config_sdk = getattr(client, "config_sdk", None)
            net_sdk = getattr(client, "sdk", None)
            if config_sdk is None or net_sdk is None:
                raise DeviceLoginError(
                    "The loaded NetSDK wrapper does not expose both native config and NetSDK libraries."
                )

            try:
                parse_fn = config_sdk.CLIENT_ParseData
                previous_argtypes = getattr(parse_fn, "argtypes", None)
                previous_restype = getattr(parse_fn, "restype", None)
                try:
                    parse_fn.argtypes = [
                        c_char_p, c_char_p, c_void_p, c_uint32, POINTER(c_uint32)
                    ]
                    parse_fn.restype = c_int
                    parsed = parse_fn(
                        command,
                        cast(input_json, c_char_p),
                        byref(access_info),
                        c_uint32(structure_size),
                        byref(parsed_size),
                    )
                finally:
                    parse_fn.argtypes = previous_argtypes
                    parse_fn.restype = previous_restype
            except Exception as exc:
                raise DeviceLoginError(
                    f"Could not call CLIENT_ParseData for AccessControl: {exc}"
                ) from exc

            if not self._as_int(parsed):
                raise DeviceLoginError(
                    "CLIENT_ParseData failed for AccessControl; "
                    f"NetSDK error={client.GetLastErrorMessage()}. No device write was attempted."
                )
            if parsed_size.value != structure_size:
                raise DeviceLoginError(
                    "Dahua parsed AccessControl into an unexpected structure size: "
                    f"returned={parsed_size.value}, expected={structure_size}. "
                    "No device write was attempted because the native layout could not be verified."
                )

            def _expected_bool(name: str) -> bool:
                value = expected_current_entry[name]
                if isinstance(value, bool):
                    return value
                if isinstance(value, (int, float)) and value in (0, 1):
                    return bool(value)
                if isinstance(value, str):
                    normalized = value.strip().lower()
                    if normalized in {"true", "1", "yes", "on"}:
                        return True
                    if normalized in {"false", "0", "no", "off", ""}:
                        return False
                raise DeviceLoginError(
                    f"AccessControl JSON field {name} has an unsupported boolean value {value!r}. "
                    "No device write was attempted."
                )

            # Cross-check all supported values that Dahua returned against
            # the native parsed structure. This validates offsets, not merely
            # the overall structure size.
            parsed_checks: dict[str, tuple[int, int]] = {}
            for field_name, native_name in native_field_map.items():
                if field_name not in expected_current_entry:
                    continue
                parsed_value = int(getattr(access_info, native_name))
                if field_name in {
                    "SensorEnable", "CloseCheckSensor", "DoorNotClosedAlarmEnable",
                    "BreakInAlarmEnable", "DuressAlarmEnable",
                }:
                    expected_value = int(_expected_bool(field_name))
                else:
                    try:
                        expected_value = int(expected_current_entry[field_name])
                    except (TypeError, ValueError) as exc:
                        raise DeviceLoginError(
                            f"AccessControl JSON field {field_name} is not an integer. "
                            "No device write was attempted."
                        ) from exc
                parsed_checks[field_name] = (parsed_value, expected_value)

            mismatched_fields = {
                field_name: values
                for field_name, values in parsed_checks.items()
                if values[0] != values[1]
            }
            if mismatched_fields:
                raise DeviceLoginError(
                    "Parsed CFG_ACCESS_EVENT_INFO does not match the current AccessControl JSON "
                    f"for field(s) {mismatched_fields!r}. No device write was attempted."
                )
            if access_info.abSensorEnable not in (0, 1):
                raise DeviceLoginError(
                    "Parsed SensorEnable capability flag has an unexpected value "
                    f"{access_info.abSensorEnable}. No device write was attempted."
                )

            # Apply only requested values. The parsed native structure retains
            # every other value, schedule, and reserved field from the device.
            for json_name, requested_value in changes.items():
                native_name = native_field_map[json_name]
                numeric_value = int(requested_value)
                if numeric_value not in (0, 1) and json_name in {
                    "SensorEnable", "CloseCheckSensor", "DoorNotClosedAlarmEnable",
                    "BreakInAlarmEnable", "DuressAlarmEnable",
                }:
                    raise ValueError(f"{json_name} must be boolean.")
                setattr(access_info, native_name, numeric_value)

                # Dahua's sample configuration writer sets the capability bit
                # when enabling a sensor. Keep it untouched for other edits.
                if json_name == "SensorEnable" and numeric_value:
                    access_info.abSensorEnable = 1

            packet_buffer = create_string_buffer(40 * 1024)
            try:
                packet_fn = config_sdk.CLIENT_PacketData
                previous_argtypes = getattr(packet_fn, "argtypes", None)
                previous_restype = getattr(packet_fn, "restype", None)
                try:
                    packet_fn.argtypes = [
                        c_char_p, c_void_p, c_uint32, c_void_p, c_uint32
                    ]
                    packet_fn.restype = c_int
                    packed = packet_fn(
                        command,
                        byref(access_info),
                        c_uint32(structure_size),
                        cast(packet_buffer, c_void_p),
                        c_uint32(sizeof(packet_buffer)),
                    )
                finally:
                    packet_fn.argtypes = previous_argtypes
                    packet_fn.restype = previous_restype
            except Exception as exc:
                raise DeviceLoginError(
                    f"Could not call CLIENT_PacketData for AccessControl: {exc}"
                ) from exc

            if not self._as_int(packed):
                raise DeviceLoginError(
                    "CLIENT_PacketData failed for AccessControl; "
                    f"NetSDK error={client.GetLastErrorMessage()}. No device write was attempted."
                )

            packet = bytes(packet_buffer).split(b"\x00", 1)[0]
            if not packet:
                raise DeviceLoginError(
                    "CLIENT_PacketData returned an empty AccessControl payload. No device write was attempted."
                )

            # Check the detailed device configuration status, not only the
            # BOOL return value. These status values are documented by Dahua.
            config_error = c_int(-1)
            restart_required = c_int(0)
            try:
                set_fn = net_sdk.CLIENT_SetNewDevConfig
                from NetSDK.SDK_Struct import C_LLONG

                previous_argtypes = getattr(set_fn, "argtypes", None)
                previous_restype = getattr(set_fn, "restype", None)
                try:
                    set_fn.argtypes = [
                        C_LLONG, c_char_p, c_int, c_char_p, c_uint32,
                        POINTER(c_int), POINTER(c_int), c_int,
                    ]
                    set_fn.restype = c_int
                    set_ok = set_fn(
                        C_LLONG(int(login_handle)),
                        command,
                        c_int(int(channel)),
                        cast(packet_buffer, c_char_p),
                        c_uint32(len(packet)),
                        byref(config_error),
                        byref(restart_required),
                        c_int(int(waittime)),
                    )
                finally:
                    set_fn.argtypes = previous_argtypes
                    set_fn.restype = previous_restype
            except Exception as exc:
                raise DeviceLoginError(
                    f"Could not call CLIENT_SetNewDevConfig for AccessControl: {exc}"
                ) from exc

            if not self._as_int(set_ok):
                raise DeviceLoginError(
                    "CLIENT_SetNewDevConfig failed for AccessControl: "
                    f"{client.GetLastErrorMessage()} (configuration status={config_error.value})."
                )

            status_messages = {
                0: "success",
                1: "failed",
                2: "illegal data",
                3: "temporarily unavailable",
                4: "permission denied",
            }
            if config_error.value != 0:
                description = status_messages.get(
                    config_error.value, "unknown configuration status"
                )
                raise DeviceLoginError(
                    "Dahua returned a non-success AccessControl configuration status: "
                    f"{config_error.value} ({description})."
                )

            return {
                "configuration_status": int(config_error.value),
                "restart_required": bool(restart_required.value),
                "structure_size": int(structure_size),
                "parsed_size": int(parsed_size.value),
            }

    def set_access_control_sensor_enabled(
        self,
        login_handle: int,
        channel: int,
        body: str,
        enabled: bool,
        expected_current_entry: dict[str, Any],
        *,
        waittime: int = 5000,
    ) -> dict[str, Any]:
        """Backward-compatible wrapper for the original sensor-only writer."""
        return self.set_access_control_config_fields(
            login_handle,
            channel,
            body,
            {"SensorEnable": bool(enabled)},
            expected_current_entry,
            waittime=waittime,
        )

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
