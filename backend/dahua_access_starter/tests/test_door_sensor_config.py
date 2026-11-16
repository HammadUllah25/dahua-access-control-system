import json
from types import SimpleNamespace

import pytest

from app.services import door_config
from app.services.dahua_sdk import DahuaSDK, DeviceLoginError


def _payload(sensor_enabled=False):
    return {
        "id": 1812,
        "params": {
            "channel": 0,
            "table": [
                {
                    "SensorEnable": sensor_enabled,
                    "CloseTimeout": 60,
                    "DoorNotClosedAlarmEnable": False,
                    "Name": "Door1",
                    "UnlockHoldInterval": 3000,
                }
            ],
        },
        "result": True,
    }


def test_get_door_sensor_reads_access_control_array(monkeypatch):
    class FakeSDK:
        def get_new_dev_config_text(self, handle, command, channel=0):
            assert handle == 123
            assert command == "AccessControl"
            assert channel == 0
            return json.dumps(_payload(sensor_enabled=False))

    monkeypatch.setattr(
        door_config.sessions,
        "connect",
        lambda device: SimpleNamespace(handle=123),
    )
    monkeypatch.setattr(door_config.sessions, "sdk", FakeSDK())

    result = door_config.get_door_sensor_config(SimpleNamespace(id=1), 0)
    assert result.sensor_enabled is False
    assert result.close_check_sensor is False
    assert result.close_timeout == 60
    assert result.door_not_closed_alarm_enable is False
    assert result.raw["Name"] == "Door1"


def test_get_door_sensor_keeps_compatibility_with_object_table(monkeypatch):
    body = {
        "params": {
            "table": {
                "SensorEnable": "false",
                "CloseCheckSensor": 0,
                "CloseTimeout": 60,
                "DoorNotClosedAlarmEnable": 0,
            }
        }
    }

    class FakeSDK:
        def get_new_dev_config_text(self, handle, command, channel=0):
            return json.dumps(body)

    monkeypatch.setattr(
        door_config.sessions,
        "connect",
        lambda device: SimpleNamespace(handle=123),
    )
    monkeypatch.setattr(door_config.sessions, "sdk", FakeSDK())

    result = door_config.get_door_sensor_config(SimpleNamespace(id=1), 0)
    assert result.sensor_enabled is False
    assert result.close_check_sensor is False


def test_set_door_sensor_changes_only_sensor_flag_and_verifies(monkeypatch):
    device_payload = _payload(sensor_enabled=False)
    submitted_payloads = []

    class FakeSDK:
        def get_new_dev_config_text(self, handle, command, channel=0):
            assert handle == 123
            assert command == "AccessControl"
            assert channel == 0
            return json.dumps(device_payload)

        def set_new_dev_config_text(
            self, handle, command, channel, body, *, restart=False, waittime=5000
        ):
            assert handle == 123
            assert command == "AccessControl"
            assert channel == 0
            assert restart is False
            submitted = json.loads(body)
            submitted_payloads.append(submitted)
            device_payload.clear()
            device_payload.update(submitted)

    fake_sdk = FakeSDK()
    monkeypatch.setattr(
        door_config.sessions,
        "connect",
        lambda device: SimpleNamespace(handle=123),
    )
    monkeypatch.setattr(door_config.sessions, "sdk", fake_sdk)

    result = door_config.set_door_sensor_config(
        SimpleNamespace(id=1), sensor_enabled=True, door_index=0
    )

    assert result.sensor_enabled is True
    assert len(submitted_payloads) == 1
    assert submitted_payloads[0]["params"]["table"][0]["SensorEnable"] is True
    assert submitted_payloads[0]["params"]["table"][0]["CloseTimeout"] == 60
    assert submitted_payloads[0]["params"]["table"][0]["Name"] == "Door1"
    assert submitted_payloads[0]["params"]["table"][0]["UnlockHoldInterval"] == 3000
    assert submitted_payloads[0]["id"] == 1812


def test_set_door_sensor_errors_when_readback_does_not_match(monkeypatch):
    device_payload = _payload(sensor_enabled=False)

    class FakeSDK:
        def get_new_dev_config_text(self, handle, command, channel=0):
            return json.dumps(device_payload)

        def set_new_dev_config_text(self, *args, **kwargs):
            # Simulate a device that reports SDK write success but ignores the setting.
            return None

    monkeypatch.setattr(
        door_config.sessions,
        "connect",
        lambda device: SimpleNamespace(handle=123),
    )
    monkeypatch.setattr(door_config.sessions, "sdk", FakeSDK())

    with pytest.raises(door_config.DoorConfigError, match="read-back verification failed"):
        door_config.set_door_sensor_config(SimpleNamespace(id=1), True, 0)


def test_netsdk_writer_passes_utf8_json_buffer_and_exact_length():
    class FakeClient:
        def SetNewDevConfig(
            self, handle, command, channel, buffer, size, error, restart, waittime
        ):
            assert handle == 123
            assert command == "AccessControl"
            assert channel == 0
            assert bytes(buffer.raw[:size]) == b'{"params":{"table":[]}}'
            assert buffer.raw[size:] == b"\x00"
            assert error == 0
            assert restart == 0
            assert waittime == 5000
            return True

    sdk = DahuaSDK()
    sdk._client = FakeClient()
    sdk._initialized = True
    sdk.set_new_dev_config_text(
        123, "AccessControl", 0, '{"params":{"table":[]}}'
    )


def test_netsdk_writer_reports_sdk_failure():
    class FakeClient:
        def SetNewDevConfig(self, *args):
            return False

        def GetLastErrorMessage(self):
            return "user parameter is illegal"

    sdk = DahuaSDK()
    sdk._client = FakeClient()
    sdk._initialized = True

    with pytest.raises(DeviceLoginError, match="user parameter is illegal"):
        sdk.set_new_dev_config_text(
            123, "AccessControl", 0, '{"params":{"table":[]}}'
        )
