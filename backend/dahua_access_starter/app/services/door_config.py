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
    door_not_closed_alarm_enable: int | bool | None
    raw: dict[str, Any]


def _read_access_control_payload(device: Device, door_index: int = 0) -> dict[str, Any]:
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

    return DoorSensorConfig(
        device_id=device.id,
        door_index=door_index,
        sensor_enabled=_as_bool(entry["SensorEnable"], "SensorEnable"),
        close_check_sensor=(
            _as_bool(entry["CloseCheckSensor"], "CloseCheckSensor")
            if "CloseCheckSensor" in entry else False
        ),
        close_timeout=close_timeout,
        door_not_closed_alarm_enable=entry.get("DoorNotClosedAlarmEnable"),
        raw=entry,
    )


def get_door_sensor_config(device: Device, door_index: int = 0) -> DoorSensorConfig:
    payload = _read_access_control_payload(device, door_index)
    return _build_config(device, door_index, payload)


def set_door_sensor_config(
    device: Device, sensor_enabled: bool, door_index: int = 0
) -> DoorSensorConfig:
    """Update only SensorEnable, then verify the value from the controller."""
    if door_index < 0:
        raise DoorConfigError("door_index must be zero or greater.")

    payload = _read_access_control_payload(device, door_index)
    entry = _select_access_control_entry(payload, door_index)

    # Preserve the full device-returned JSON envelope and all unmodified door
    # parameters. Only SensorEnable is changed in the selected door entry.
    entry["SensorEnable"] = bool(sensor_enabled)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    try:
        session = sessions.connect(device)
        sessions.sdk.set_new_dev_config_text(
            session.handle,
            "AccessControl",
            door_index,
            serialized,
            restart=False,
        )
    except Exception as exc:
        raise DoorConfigError(
            f"Could not write AccessControl through Dahua NetSDK: {exc}"
        ) from exc

    # A successful SDK return is not sufficient; verify that the controller
    # reports the requested value after the write.
    verified = get_door_sensor_config(device, door_index)
    if verified.sensor_enabled is not bool(sensor_enabled):
        raise DoorConfigError(
            "Dahua accepted the AccessControl write, but read-back verification "
            f"failed: SensorEnable is {verified.sensor_enabled}, requested {bool(sensor_enabled)}."
        )
    return verified
