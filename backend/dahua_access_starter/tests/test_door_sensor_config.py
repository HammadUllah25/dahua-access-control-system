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


def test_get_door_config_exposes_alarm_types_and_unlock_duration(monkeypatch):
    body = {
        "params": {
            "table": [{
                "SensorEnable": True,
                "CloseCheckSensor": True,
                "CloseTimeout": 60,
                "DoorNotClosedAlarmEnable": True,
                "BreakInAlarmEnable": False,
                "DuressAlarmEnable": True,
                "UnlockHoldInterval": 2200,
            }]
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
    assert result.forced_entry_alarm_enable is False
    assert result.door_not_closed_alarm_enable is True
    assert result.duress_alarm_enable is True
    assert result.alarm_enabled is True
    assert result.unlock_duration_seconds == 2.2


def test_set_door_sensor_uses_structured_sdk_write_and_verifies(monkeypatch):
    device_payload = _payload(sensor_enabled=False)
    initial_body = json.dumps(device_payload)
    writes = []

    class FakeSDK:
        def get_new_dev_config_text(self, handle, command, channel=0):
            assert handle == 123
            assert command == "AccessControl"
            assert channel == 0
            return json.dumps(device_payload)

        def set_access_control_sensor_enabled(
            self, handle, channel, body, enabled, expected_current_entry, *, waittime=5000
        ):
            assert handle == 123
            assert channel == 0
            assert body == initial_body
            assert enabled is True
            assert expected_current_entry["SensorEnable"] is False
            writes.append((body, enabled))
            device_payload["params"]["table"][0]["SensorEnable"] = enabled
            return {"configuration_status": 0, "restart_required": False}

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
    assert len(writes) == 1
    # The service passes Dahua's original JSON to ParseData; it no longer
    # edits and submits raw AccessControl JSON directly to SetNewDevConfig.
    assert writes[0][0] == initial_body
    assert device_payload["params"]["table"][0]["CloseTimeout"] == 60
    assert device_payload["params"]["table"][0]["Name"] == "Door1"
    assert device_payload["params"]["table"][0]["UnlockHoldInterval"] == 3000
    assert device_payload["id"] == 1812


def test_set_door_sensor_errors_when_readback_does_not_match(monkeypatch):
    device_payload = _payload(sensor_enabled=False)

    class FakeSDK:
        def get_new_dev_config_text(self, handle, command, channel=0):
            return json.dumps(device_payload)

        def set_access_control_sensor_enabled(self, *args, **kwargs):
            # Simulate a controller that reports write success but retains false.
            return {"configuration_status": 0, "restart_required": False}

    monkeypatch.setattr(
        door_config.sessions,
        "connect",
        lambda device: SimpleNamespace(handle=123),
    )
    monkeypatch.setattr(door_config.sessions, "sdk", FakeSDK())

    with pytest.raises(door_config.DoorConfigError, match="read-back verification failed"):
        door_config.set_door_sensor_config(SimpleNamespace(id=1), True, 0)


def test_set_multiple_door_options_and_verify_readback(monkeypatch):
    device_payload = _payload(sensor_enabled=True)
    entry = device_payload["params"]["table"][0]
    entry.update({
        "CloseCheckSensor": False,
        "BreakInAlarmEnable": False,
        "DuressAlarmEnable": False,
    })
    writes = []

    class FakeSDK:
        def get_new_dev_config_text(self, handle, command, channel=0):
            return json.dumps(device_payload)

        def set_access_control_config_fields(
            self, handle, channel, body, changes, expected_current_entry, *, waittime=5000
        ):
            assert channel == 0
            assert expected_current_entry["UnlockHoldInterval"] == 3000
            writes.append(changes.copy())
            for key, value in changes.items():
                entry[key] = value
            return {"configuration_status": 0, "restart_required": False}

    monkeypatch.setattr(
        door_config.sessions,
        "connect",
        lambda device: SimpleNamespace(handle=123),
    )
    monkeypatch.setattr(door_config.sessions, "sdk", FakeSDK())

    result = door_config.set_door_sensor_config(
        SimpleNamespace(id=1),
        door_index=0,
        changes={
            "close_check_sensor": True,
            "close_timeout": 45,
            "door_not_closed_alarm_enable": True,
            "forced_entry_alarm_enable": True,
            "duress_alarm_enable": False,
            "unlock_duration_seconds": 2.5,
        },
    )

    assert len(writes) == 1
    assert writes[0] == {
        "CloseCheckSensor": True,
        "CloseTimeout": 45,
        "DoorNotClosedAlarmEnable": True,
        "BreakInAlarmEnable": True,
        "DuressAlarmEnable": False,
        "UnlockHoldInterval": 2500,
    }
    assert result.close_check_sensor is True
    assert result.close_timeout == 45
    assert result.door_not_closed_alarm_enable is True
    assert result.forced_entry_alarm_enable is True
    assert result.duress_alarm_enable is False
    assert result.unlock_duration_seconds == 2.5


def test_access_event_structure_has_expected_sensor_field_offsets():
    from ctypes import sizeof
    from app.services.dahua_access_control_structs import (
        CFG_ACCESS_EVENT_INFO,
        CFG_ACCESS_EVENT_INFO_EXPECTED_SIZE,
        CFG_ACCESS_EVENT_INFO_SENSOR_CAPABILITY_OFFSET,
        CFG_ACCESS_EVENT_INFO_SENSOR_VALUE_OFFSET,
    )

    assert sizeof(CFG_ACCESS_EVENT_INFO) == CFG_ACCESS_EVENT_INFO_EXPECTED_SIZE == 3672
    assert CFG_ACCESS_EVENT_INFO.abSensorEnable.offset == CFG_ACCESS_EVENT_INFO_SENSOR_CAPABILITY_OFFSET == 155
    assert CFG_ACCESS_EVENT_INFO.bSensorEnable.offset == CFG_ACCESS_EVENT_INFO_SENSOR_VALUE_OFFSET == 2332


def test_structured_sensor_writer_uses_parse_packet_and_status(monkeypatch):
    import ctypes
    import sys
    import types

    from app.services.dahua_access_control_structs import CFG_ACCESS_EVENT_INFO

    class NativeFunction:
        def __init__(self, callback):
            self.callback = callback
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            return self.callback(*args)

    observed = {}

    def parse(command, input_json, output_ptr, output_size, parsed_size_ptr):
        assert command == b"AccessControl"
        assert output_size.value == ctypes.sizeof(CFG_ACCESS_EVENT_INFO)
        parsed = ctypes.cast(output_ptr, ctypes.POINTER(CFG_ACCESS_EVENT_INFO)).contents
        parsed.abSensorEnable = 0
        parsed.bSensorEnable = 0
        parsed.nCloseTimeout = 60
        parsed.nUnlockHoldInterval = 3000
        parsed.bDoorNotClosedAlarmEnable = 0
        ctypes.cast(parsed_size_ptr, ctypes.POINTER(ctypes.c_uint32)).contents.value = ctypes.sizeof(CFG_ACCESS_EVENT_INFO)
        observed["parsed"] = True
        return 1

    def packet(command, input_ptr, input_size, output_ptr, output_size):
        assert command == b"AccessControl"
        assert input_size.value == ctypes.sizeof(CFG_ACCESS_EVENT_INFO)
        parsed = ctypes.cast(input_ptr, ctypes.POINTER(CFG_ACCESS_EVENT_INFO)).contents
        observed["capability"] = parsed.abSensorEnable
        observed["sensor_value"] = parsed.bSensorEnable
        observed["close_timeout"] = parsed.nCloseTimeout
        out = ctypes.cast(output_ptr, ctypes.POINTER(ctypes.c_char))
        packed = b'{"params":{"table":[{"SensorEnable":true}]}}\x00'
        ctypes.memmove(out, packed, len(packed))
        return 1

    def set_config(handle, command, channel, input_ptr, input_size, error_ptr, restart_ptr, waittime):
        assert handle.value == 123
        assert command == b"AccessControl"
        assert channel.value == 0
        assert input_size.value == 44
        ctypes.cast(error_ptr, ctypes.POINTER(ctypes.c_int)).contents.value = 0
        ctypes.cast(restart_ptr, ctypes.POINTER(ctypes.c_int)).contents.value = 0
        observed["set_called"] = True
        return 1

    fake_net_sdk = types.SimpleNamespace(
        CLIENT_SetNewDevConfig=NativeFunction(set_config)
    )
    fake_config_sdk = types.SimpleNamespace(
        CLIENT_ParseData=NativeFunction(parse),
        CLIENT_PacketData=NativeFunction(packet),
    )
    fake_client = types.SimpleNamespace(
        config_sdk=fake_config_sdk,
        sdk=fake_net_sdk,
        GetLastErrorMessage=lambda: "test error",
    )

    netsdk_pkg = types.ModuleType("NetSDK")
    netsdk_pkg.__path__ = []
    netsdk_struct = types.ModuleType("NetSDK.SDK_Struct")
    netsdk_struct.C_LLONG = ctypes.c_longlong
    monkeypatch.setitem(sys.modules, "NetSDK", netsdk_pkg)
    monkeypatch.setitem(sys.modules, "NetSDK.SDK_Struct", netsdk_struct)

    sdk = DahuaSDK()
    sdk._client = fake_client
    sdk._initialized = True
    result = sdk.set_access_control_sensor_enabled(
        123, 0,
        '{"params":{"table":[]}}', True,
        {"SensorEnable": False, "CloseTimeout": 60},
    )

    assert observed == {
        "parsed": True,
        "capability": 1,
        "sensor_value": 1,
        "close_timeout": 60,
        "set_called": True,
    }
    assert result["configuration_status"] == 0
    assert result["restart_required"] is False


def test_structured_door_writer_updates_alarm_timeout_and_unlock_duration(monkeypatch):
    import ctypes
    import sys
    import types

    from app.services.dahua_access_control_structs import CFG_ACCESS_EVENT_INFO

    class NativeFunction:
        def __init__(self, callback):
            self.callback = callback
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            return self.callback(*args)

    observed = {}

    def parse(command, input_json, output_ptr, output_size, parsed_size_ptr):
        parsed = ctypes.cast(output_ptr, ctypes.POINTER(CFG_ACCESS_EVENT_INFO)).contents
        parsed.abSensorEnable = 1
        parsed.bSensorEnable = 1
        parsed.bCloseCheckSensor = 0
        parsed.nCloseTimeout = 60
        parsed.nUnlockHoldInterval = 3000
        parsed.bDoorNotClosedAlarmEnable = 0
        parsed.bBreakInAlarmEnable = 0
        parsed.bDuressAlarmEnable = 0
        ctypes.cast(parsed_size_ptr, ctypes.POINTER(ctypes.c_uint32)).contents.value = ctypes.sizeof(CFG_ACCESS_EVENT_INFO)
        return 1

    def packet(command, input_ptr, input_size, output_ptr, output_size):
        parsed = ctypes.cast(input_ptr, ctypes.POINTER(CFG_ACCESS_EVENT_INFO)).contents
        observed.update({
            "sensor": parsed.bSensorEnable,
            "close_check": parsed.bCloseCheckSensor,
            "close_timeout": parsed.nCloseTimeout,
            "unlock_interval": parsed.nUnlockHoldInterval,
            "timed_out_alarm": parsed.bDoorNotClosedAlarmEnable,
            "forced_entry_alarm": parsed.bBreakInAlarmEnable,
            "duress_alarm": parsed.bDuressAlarmEnable,
        })
        packed = b'{"params":{"table":[{}]}}\x00'
        ctypes.memmove(output_ptr, packed, len(packed))
        return 1

    def set_config(handle, command, channel, input_ptr, input_size, error_ptr, restart_ptr, waittime):
        ctypes.cast(error_ptr, ctypes.POINTER(ctypes.c_int)).contents.value = 0
        ctypes.cast(restart_ptr, ctypes.POINTER(ctypes.c_int)).contents.value = 0
        return 1

    fake_client = types.SimpleNamespace(
        config_sdk=types.SimpleNamespace(
            CLIENT_ParseData=NativeFunction(parse),
            CLIENT_PacketData=NativeFunction(packet),
        ),
        sdk=types.SimpleNamespace(CLIENT_SetNewDevConfig=NativeFunction(set_config)),
        GetLastErrorMessage=lambda: "test error",
    )
    netsdk_pkg = types.ModuleType("NetSDK")
    netsdk_pkg.__path__ = []
    netsdk_struct = types.ModuleType("NetSDK.SDK_Struct")
    netsdk_struct.C_LLONG = ctypes.c_longlong
    monkeypatch.setitem(sys.modules, "NetSDK", netsdk_pkg)
    monkeypatch.setitem(sys.modules, "NetSDK.SDK_Struct", netsdk_struct)

    sdk = DahuaSDK()
    sdk._client = fake_client
    sdk._initialized = True
    result = sdk.set_access_control_config_fields(
        123,
        0,
        '{"params":{"table":[{}]}}',
        {
            "CloseCheckSensor": 1,
            "CloseTimeout": 45,
            "UnlockHoldInterval": 2500,
            "DoorNotClosedAlarmEnable": 1,
            "BreakInAlarmEnable": 1,
            "DuressAlarmEnable": 1,
        },
        {
            "SensorEnable": True,
            "CloseCheckSensor": False,
            "CloseTimeout": 60,
            "UnlockHoldInterval": 3000,
            "DoorNotClosedAlarmEnable": False,
            "BreakInAlarmEnable": False,
            "DuressAlarmEnable": False,
        },
    )

    assert observed == {
        "sensor": 1,
        "close_check": 1,
        "close_timeout": 45,
        "unlock_interval": 2500,
        "timed_out_alarm": 1,
        "forced_entry_alarm": 1,
        "duress_alarm": 1,
    }
    assert result["configuration_status"] == 0
    assert result["restart_required"] is False


def test_structured_sensor_writer_refuses_write_if_layout_size_differs(monkeypatch):
    import ctypes
    import sys
    import types

    class NativeFunction:
        def __init__(self, callback):
            self.callback = callback
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            return self.callback(*args)

    set_calls = []

    def parse(command, input_json, output_ptr, output_size, parsed_size_ptr):
        ctypes.cast(parsed_size_ptr, ctypes.POINTER(ctypes.c_uint32)).contents.value = 100
        return 1

    def set_config(*args):
        set_calls.append(args)
        return 1

    fake_client = types.SimpleNamespace(
        config_sdk=types.SimpleNamespace(
            CLIENT_ParseData=NativeFunction(parse),
            CLIENT_PacketData=NativeFunction(lambda *args: 1),
        ),
        sdk=types.SimpleNamespace(CLIENT_SetNewDevConfig=NativeFunction(set_config)),
        GetLastErrorMessage=lambda: "test error",
    )
    netsdk_pkg = types.ModuleType("NetSDK")
    netsdk_pkg.__path__ = []
    netsdk_struct = types.ModuleType("NetSDK.SDK_Struct")
    netsdk_struct.C_LLONG = ctypes.c_longlong
    monkeypatch.setitem(sys.modules, "NetSDK", netsdk_pkg)
    monkeypatch.setitem(sys.modules, "NetSDK.SDK_Struct", netsdk_struct)

    sdk = DahuaSDK()
    sdk._client = fake_client
    sdk._initialized = True

    with pytest.raises(DeviceLoginError, match="unexpected structure size"):
        sdk.set_access_control_sensor_enabled(
            123, 0, '{"params":{"table":[]}}', True, {"SensorEnable": False}
        )
    assert set_calls == []


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
