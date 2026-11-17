from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.models.device import Device
from app.services.device_sessions import sessions


class DoorConfigError(RuntimeError):
    pass


@dataclass
class DoorSensorConfig:
    device_id: int
    door_index: int
    sensor_enabled: bool
    close_check_sensor: bool
    close_timeout: int | None
    door_not_closed_alarm_enable: bool | None
    forced_entry_alarm_enable: bool | None
    duress_alarm_enable: bool | None
    unlock_duration_seconds: float | None
    raw: dict[str, Any]

    @property
    def alarm_enabled(self) -> bool | None:
        """SmartPSS parent switch is represented by its individual alarm types."""
        alarm_values = (
            self.forced_entry_alarm_enable,
            self.door_not_closed_alarm_enable,
            self.duress_alarm_enable,
        )
        known_values = [value for value in alarm_values if value is not None]
        return any(known_values) if known_values else None


def _read_access_control_body(device: Device, door_index: int = 0) -> str:
    if door_index < 0:
        raise DoorConfigError("door_index must be zero or greater.")

    try:
        session = sessions.connect(device)
        body = sessions.sdk.get_new_dev_config_text(
            session.handle, "AccessControl", channel=door_index
        )
    except Exception as exc:
        raise DoorConfigError(
            f"Could not read AccessControl through Dahua NetSDK: {exc}"
        ) from exc
    return body


def _parse_access_control_payload(body: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise TypeError("configuration response is not a JSON object")
        params = payload.get("params")
        if not isinstance(params, dict):
            raise TypeError("configuration response does not contain a params object")
        table = params.get("table")
        if not isinstance(table, (dict, list)):
            raise TypeError("configuration table is neither an object nor an array")
        return payload
    except (json.JSONDecodeError, TypeError) as exc:
        raise DoorConfigError(
            f"Dahua returned an unexpected AccessControl payload: {exc}; "
            f"response={body[:1000]!r}"
        ) from exc


def _read_access_control_payload(device: Device, door_index: int = 0) -> dict[str, Any]:
    body = _read_access_control_body(device, door_index)
    return _parse_access_control_payload(body)


def _select_access_control_entry(
    payload: dict[str, Any], door_index: int
) -> dict[str, Any]:
    table = payload["params"]["table"]

    # Dahua firmware commonly returns AccessControl as an array, even when the
    # device has only one door. Some firmware revisions return a single object.
    if isinstance(table, dict):
        return table

    if not table:
        raise DoorConfigError("AccessControl response contains an empty table.")

    selected_index = door_index if door_index < len(table) else 0 if len(table) == 1 else -1
    if selected_index < 0:
        raise DoorConfigError(
            f"AccessControl response has {len(table)} door entries; "
            f"door_index {door_index} is unavailable."
        )

    entry = table[selected_index]
    if not isinstance(entry, dict):
        raise DoorConfigError(
            f"AccessControl table entry for door_index {door_index} is not an object."
        )
    return entry


def _as_bool(value: Any, field_name: str) -> bool:
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
    raise DoorConfigError(
        f"AccessControl field {field_name} has an unsupported boolean value: {value!r}."
    )


def _build_config(
    device: Device,
    door_index: int,
    payload: dict[str, Any],
) -> DoorSensorConfig:
    entry = _select_access_control_entry(payload, door_index)
    if "SensorEnable" not in entry:
        raise DoorConfigError("AccessControl response does not contain SensorEnable.")

    close_timeout_value = entry.get("CloseTimeout")
    try:
        close_timeout = int(close_timeout_value) if close_timeout_value is not None else None
    except (TypeError, ValueError) as exc:
        raise DoorConfigError(
            f"AccessControl field CloseTimeout has an invalid value: {close_timeout_value!r}."
        ) from exc

    unlock_hold_value = entry.get("UnlockHoldInterval")
    try:
        # Dahua CFG_ACCESS_EVENT_INFO.nUnlockHoldInterval is represented in
        # milliseconds (e.g. 2000 == 2.0 seconds in SmartPSS).
        unlock_duration_seconds = (
            float(unlock_hold_value) / 1000.0
            if unlock_hold_value is not None else None
        )
    except (TypeError, ValueError) as exc:
        raise DoorConfigError(
            "AccessControl field UnlockHoldInterval has an invalid value: "
            f"{unlock_hold_value!r}."
        ) from exc

    def optional_bool(field_name: str) -> bool | None:
        if field_name not in entry:
            return None
        return _as_bool(entry[field_name], field_name)

    return DoorSensorConfig(
        device_id=device.id,
        door_index=door_index,
        sensor_enabled=_as_bool(entry["SensorEnable"], "SensorEnable"),
        close_check_sensor=(
            _as_bool(entry["CloseCheckSensor"], "CloseCheckSensor")
            if "CloseCheckSensor" in entry else False
        ),
        close_timeout=close_timeout,
        door_not_closed_alarm_enable=optional_bool("DoorNotClosedAlarmEnable"),
        forced_entry_alarm_enable=optional_bool("BreakInAlarmEnable"),
        duress_alarm_enable=optional_bool("DuressAlarmEnable"),
        unlock_duration_seconds=unlock_duration_seconds,
        raw=entry,
    )


def get_door_sensor_config(device: Device, door_index: int = 0) -> DoorSensorConfig:
    payload = _read_access_control_payload(device, door_index)
    return _build_config(device, door_index, payload)


def set_door_sensor_config(
    device: Device,
    sensor_enabled: bool | None = None,
    door_index: int = 0,
    *,
    changes: dict[str, bool | int | float] | None = None,
) -> DoorSensorConfig:
    """Update supported door options, preserving all other native fields.

    ``sensor_enabled`` remains as a compatibility argument for existing callers.
    New callers should pass the optional API fields through ``changes``.
    """
    if door_index < 0:
        raise DoorConfigError("door_index must be zero or greater.")

    if changes is None:
        if sensor_enabled is None:
            raise DoorConfigError("At least one door configuration field is required.")
        changes = {"sensor_enabled": sensor_enabled}
    elif sensor_enabled is not None:
        changes = {**changes, "sensor_enabled": sensor_enabled}

    api_to_device_field = {
        "sensor_enabled": "SensorEnable",
        "close_check_sensor": "CloseCheckSensor",
        "close_timeout": "CloseTimeout",
        "door_not_closed_alarm_enable": "DoorNotClosedAlarmEnable",
        "forced_entry_alarm_enable": "BreakInAlarmEnable",
        "duress_alarm_enable": "DuressAlarmEnable",
        "unlock_duration_seconds": "UnlockHoldInterval",
    }
    unknown_fields = set(changes) - set(api_to_device_field)
    if unknown_fields:
        raise DoorConfigError(
            f"Unsupported door configuration field(s): {sorted(unknown_fields)}."
        )

    native_changes: dict[str, bool | int] = {}
    for api_field, requested_value in changes.items():
        device_field = api_to_device_field[api_field]
        if api_field == "unlock_duration_seconds":
            native_changes[device_field] = int(round(float(requested_value) * 1000))
        elif api_field == "close_timeout":
            native_changes[device_field] = int(requested_value)
        else:
            native_changes[device_field] = bool(requested_value)

    # Validate the device's current response and keep the exact JSON returned
    # by Dahua for CLIENT_ParseData. We do not rebuild this envelope manually.
    body = _read_access_control_body(device, door_index)
    payload = _parse_access_control_payload(body)
    entry = _select_access_control_entry(payload, door_index)
    for field_name in native_changes:
        if field_name not in entry:
            raise DoorConfigError(
                f"This controller's AccessControl response does not expose "
                f"{field_name}; no device write was attempted."
            )

    try:
        session = sessions.connect(device)
        if set(native_changes) == {"SensorEnable"} and hasattr(
            sessions.sdk, "set_access_control_sensor_enabled"
        ):
            # Keep compatibility with the previously shipped sensor-only SDK
            # adapter and its test doubles.
            write_result = sessions.sdk.set_access_control_sensor_enabled(
                session.handle,
                door_index,
                body,
                bool(native_changes["SensorEnable"]),
                entry,
            )
        else:
            write_result = sessions.sdk.set_access_control_config_fields(
                session.handle,
                door_index,
                body,
                native_changes,
                entry,
            )
    except Exception as exc:
        raise DoorConfigError(
            f"Could not write structured AccessControl sensor configuration through Dahua NetSDK: {exc}"
        ) from exc

    if write_result.get("restart_required"):
        raise DoorConfigError(
            "Dahua reported that the AccessControl sensor configuration requires a device restart. "
            "The API did not restart the controller automatically; read-back verification is deferred."
        )

    # A successful SDK return and status code are still not enough: verify
    # the actual value returned by the controller after the write.
    verified = get_door_sensor_config(device, door_index)
    verified_values = {
        "sensor_enabled": verified.sensor_enabled,
        "close_check_sensor": verified.close_check_sensor,
        "close_timeout": verified.close_timeout,
        "door_not_closed_alarm_enable": verified.door_not_closed_alarm_enable,
        "forced_entry_alarm_enable": verified.forced_entry_alarm_enable,
        "duress_alarm_enable": verified.duress_alarm_enable,
        "unlock_duration_seconds": verified.unlock_duration_seconds,
    }
    mismatches: dict[str, tuple[Any, Any]] = {}
    for field_name, requested_value in changes.items():
        actual_value = verified_values[field_name]
        expected_value: Any = requested_value
        if field_name == "unlock_duration_seconds":
            expected_value = int(round(float(requested_value) * 1000)) / 1000.0
            if actual_value is not None and abs(actual_value - expected_value) < 0.001:
                continue
        elif field_name in {
            "sensor_enabled", "close_check_sensor", "door_not_closed_alarm_enable",
            "forced_entry_alarm_enable", "duress_alarm_enable",
        }:
            expected_value = bool(requested_value)
        else:
            expected_value = int(requested_value)
        if actual_value != expected_value:
            mismatches[field_name] = (actual_value, expected_value)
    if mismatches:
        raise DoorConfigError(
            "AccessControl read-back verification failed for requested field(s): "
            f"{mismatches!r}."
        )
    return verified

