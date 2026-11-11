"""Offline smoke test for the discovery/account-init orchestration.

Uses the installed NetSDK ctypes declarations but mocks native NetSDK calls.
It does not load Dahua DLLs or touch a physical controller.
"""
from __future__ import annotations

from ctypes import pointer
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from NetSDK.SDK_Struct import DEVICE_NET_INFO_EX2
from app.services.device_initialization import DeviceInitializationService


class FakeClient:
    def __init__(self):
        self.init_call = None
        self.callback = None

    def StartSearchDevicesEx(self, search_in, search_out):
        self.callback = search_in.cbSearchDevices
        result = DEVICE_NET_INFO_EX2()
        result.stuDevInfo.iIPVersion = 4
        result.stuDevInfo.szIP = b"192.168.0.200"
        result.stuDevInfo.nPort = 37777
        result.stuDevInfo.nHttpPort = 80
        result.stuDevInfo.szMac = b"AA:BB:CC:DD:EE:FF"
        result.stuDevInfo.szSerialNo = b"TESTSERIAL123"
        result.stuDevInfo.szDetailType = b"ASI1201E"
        result.stuDevInfo.byInitStatus = 1
        result.stuDevInfo.byPwdResetWay = 3
        result.szLocalIP = b"192.168.0.10"
        search_in.cbSearchDevices(123, pointer(result), None)
        return 123

    def StopSearchDevices(self, handle):
        return 1

    def InitDevAccount(self, init_in, init_out, wait_ms, local_ip):
        self.init_call = {
            "mac": bytes(init_in.szMac).split(b"\0", 1)[0].decode(),
            "username": bytes(init_in.szUserName).split(b"\0", 1)[0].decode(),
            "password": bytes(init_in.szPwd).split(b"\0", 1)[0].decode(),
            "flags": int(init_in.byPwdResetWay),
            "local_ip": (local_ip.value if hasattr(local_ip, "value") else local_ip).decode() if isinstance((local_ip.value if hasattr(local_ip, "value") else local_ip), bytes) else str(local_ip),
            "wait_ms": int(wait_ms),
        }
        return 1

    def GetLastError(self):
        return 0

    def GetLastErrorMessage(self):
        return "No error"


class FakeSDKAdapter:
    def __init__(self):
        self.client = FakeClient()

    def initialize(self):
        return None


adapter = FakeSDKAdapter()
service = DeviceInitializationService(adapter)
result = service.discover(local_ip="192.168.0.10", wait_seconds=2)
assert result["count"] == 1, result
found = result["devices"][0]
assert found["initialization_state"] == "uninitialized", found
assert found["supports_phone_reset"] and found["supports_email_reset"], found

initialized = service.initialize_device(
    mac_address=found["mac_address"],
    local_ip=found["local_ip"],
    username="admin",
    password="TestPassword!123",
    confirm_password="TestPassword!123",
    cellphone="03001234567",
    email="admin@example.com",
)
assert initialized["success"] is True, initialized
assert adapter.client.init_call["mac"] == "AA:BB:CC:DD:EE:FF"
assert adapter.client.init_call["flags"] == 3
assert adapter.client.init_call["local_ip"] == "192.168.0.10"
print("PASS: mocked discovery callback and InitDevAccount parameter flow.")
