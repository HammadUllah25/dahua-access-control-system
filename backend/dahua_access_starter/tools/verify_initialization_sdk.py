"""Verify that the installed Dahua NetSDK wheel exposes the initialization API layout.

This check imports Python ctypes declarations only. It does not load the native DLL,
search the network, initialize an account, or change a physical controller.
"""
from __future__ import annotations

from ctypes import sizeof

from NetSDK.SDK_Callback import fSearchDevicesCBEx
from NetSDK.SDK_Enum import EM_ACCOUNT_PROTOCOL, EM_SEND_SEARCH_TYPE
from NetSDK.SDK_Struct import (
    DEVICE_NET_INFO_EX,
    DEVICE_NET_INFO_EX2,
    NET_IN_INIT_DEVICE_ACCOUNT,
    NET_OUT_INIT_DEVICE_ACCOUNT,
    NET_IN_STARTSERACH_DEVICE,
    NET_OUT_STARTSERACH_DEVICE,
)


def fields(structure):
    return {name for name, _field_type in structure._fields_}


checks = {
    "DEVICE_NET_INFO_EX": {"szIP", "nPort", "szMac", "szSerialNo", "byInitStatus", "byPwdResetWay"},
    "DEVICE_NET_INFO_EX2": {"stuDevInfo", "szLocalIP"},
    "NET_IN_STARTSERACH_DEVICE": {"dwSize", "szLocalIp", "cbSearchDevices", "emSendType"},
    "NET_OUT_STARTSERACH_DEVICE": {"dwSize"},
    "NET_IN_INIT_DEVICE_ACCOUNT": {"dwSize", "szMac", "szUserName", "szPwd", "szCellPhone", "szMail", "byPwdResetWay", "emAccountProtocol"},
    "NET_OUT_INIT_DEVICE_ACCOUNT": {"dwSize"},
}

structures = {
    "DEVICE_NET_INFO_EX": DEVICE_NET_INFO_EX,
    "DEVICE_NET_INFO_EX2": DEVICE_NET_INFO_EX2,
    "NET_IN_STARTSERACH_DEVICE": NET_IN_STARTSERACH_DEVICE,
    "NET_OUT_STARTSERACH_DEVICE": NET_OUT_STARTSERACH_DEVICE,
    "NET_IN_INIT_DEVICE_ACCOUNT": NET_IN_INIT_DEVICE_ACCOUNT,
    "NET_OUT_INIT_DEVICE_ACCOUNT": NET_OUT_INIT_DEVICE_ACCOUNT,
}

for name, expected in checks.items():
    actual = fields(structures[name])
    missing = expected - actual
    if missing:
        raise SystemExit(f"FAIL {name}: missing fields {sorted(missing)}")
    print(f"OK {name}: {sizeof(structures[name])} bytes; required fields present")

assert int(EM_SEND_SEARCH_TYPE.MULTICAST_AND_BROADCAST) == 0
assert int(EM_ACCOUNT_PROTOCOL.ACCOUNT_PROTOCOL_NORMAL) == 0
assert callable(fSearchDevicesCBEx)
print("OK Search callback and required enum values are available.")
print("PASS: SDK declarations match this project's initialization module.")
