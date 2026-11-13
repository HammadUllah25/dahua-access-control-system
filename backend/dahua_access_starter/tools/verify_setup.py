from __future__ import annotations

import sys


def main() -> int:
    print(f"Python executable: {sys.executable}")
    try:
        from NetSDK.SDK_Enum import CtrlType, EM_NET_RECORD_TYPE
        from NetSDK.SDK_Struct import NET_RECORDSET_ACCESS_CTL_CARD
        from NetSDK.NetSDK import NetClient
    except Exception as exc:
        print(f"FAIL: Could not import the Dahua NetSDK wrapper: {exc}")
        return 1

    from ctypes import sizeof

    print("PASS: NetSDK wrapper imports.")
    print(f"PASS: NET_RECORDSET_ACCESS_CTL_CARD size = {sizeof(NET_RECORDSET_ACCESS_CTL_CARD)} bytes.")
    print(f"PASS: RECORDSET_INSERT enum = {int(CtrlType.RECORDSET_INSERT)}")
    print(f"PASS: ACCESSCTLCARD record enum = {int(EM_NET_RECORD_TYPE.ACCESSCTLCARD)}")
    print("NOTE: This checks the local Python package only; it does not log in to or modify a physical controller.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
