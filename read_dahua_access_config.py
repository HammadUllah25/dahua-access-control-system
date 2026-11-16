"""Read-only NetSDK configuration probe for a Dahua ASI1201E.

This script DOES NOT write settings, enroll cards, reboot the controller, or
change door/lock behavior. It only logs in and queries configuration text.

Run from the project root using the project's Windows virtual environment:
  .\\backend\\dahua_access_starter\\.venv\\Scripts\\python.exe read_dahua_access_config.py
"""

from ctypes import c_char, sizeof
from getpass import getpass
import json
from pathlib import Path

from NetSDK.NetSDK import NetClient
from NetSDK.SDK_Enum import EM_LOGIN_SPAC_CAP_TYPE
from NetSDK.SDK_Struct import (
    NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY,
    NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY,
)


def main() -> int:
    log_lines = []

    def emit(message: str = "") -> None:
        print(message)
        log_lines.append(message)

    ip = input("Device IP [192.168.0.2]: ").strip() or "192.168.0.2"
    port_text = input("NetSDK port [37777]: ").strip() or "37777"
    username = input("Username [admin]: ").strip() or "admin"
    password = getpass("Device password: ")

    sdk = NetClient()
    login_id = 0
    initialized = bool(sdk.InitEx())
    if not initialized:
        emit("SDK initialization failed: " + sdk.GetLastErrorMessage())
        Path("door_config_probe.txt").write_text("\n".join(log_lines), encoding="utf-8")
        return 1

    try:
        in_param = NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY()
        in_param.dwSize = sizeof(NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY)
        in_param.szIP = ip.encode()
        in_param.nPort = int(port_text)
        in_param.szUserName = username.encode()
        in_param.szPassword = password.encode()
        in_param.emSpecCap = EM_LOGIN_SPAC_CAP_TYPE.TCP
        in_param.pCapParam = None

        out_param = NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY()
        out_param.dwSize = sizeof(NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY)

        login_id, device_info, error_message = sdk.LoginWithHighLevelSecurity(
            in_param, out_param
        )
        if not login_id:
            emit("Device login failed: " + str(error_message))
            Path("door_config_probe.txt").write_text("\n".join(log_lines), encoding="utf-8")
            return 2

        emit("\nLogin successful. Read-only queries starting.")
        emit("No configuration will be changed.\n")

        # AccessControl is a candidate command found in the supplied Dahua
        # dhconfigsdk.dll / dhnetsdk.dll. Alarm is the documented Python SDK
        # external-alarm command and is queried only for comparison.
        probes = [
            ("AccessControl", 0),
            ("AccessControl", -1),
            ("Alarm", 0),
            ("Alarm", -1),
        ]

        for command, channel in probes:
            emit(f"=== command={command!r}, channel={channel} ===")
            out_buffer = (c_char * 262144)()
            ok = sdk.GetNewDevConfig(
                login_id,
                command,
                channel,
                out_buffer,
                sizeof(out_buffer),
                0,
                5000,
            )
            if not ok:
                emit("QUERY FAILED: " + sdk.GetLastErrorMessage() + "\n")
                continue

            raw = bytes(out_buffer)
            # Remove only trailing NUL padding; preserve embedded content.
            raw = raw.rstrip(b"\x00")
            emit(f"QUERY SUCCEEDED; returned buffer bytes: {len(raw)}")
            decoded = raw.decode("utf-8", errors="replace").strip()
            try:
                parsed = json.loads(decoded)
                emit(json.dumps(parsed, indent=2, ensure_ascii=False))
            except Exception:
                emit(decoded[:20000] if decoded else "<empty response>")
            emit()

        emit("Read-only probe finished.")
        Path("door_config_probe.txt").write_text("\n".join(log_lines), encoding="utf-8")
        print("Saved output to door_config_probe.txt")
        return 0

    finally:
        if login_id:
            sdk.Logout(login_id)
        sdk.Cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
