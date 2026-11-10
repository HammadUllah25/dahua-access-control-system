"""Verify that the installed Dahua NetSDK wheel exposes the IC-card APIs.

This checks Python enums and ctypes structure declarations only. It does not
initialize the native SDK or write anything to a physical controller.
Run on the Windows machine with the same venv used by the API.
"""
from __future__ import annotations

from ctypes import sizeof

from NetSDK.SDK_Enum import (
    CtrlType,
    EM_NET_RECORD_TYPE,
    EM_A_NET_ACCESSCTLCARD_STATE,
    EM_A_NET_ACCESSCTLCARD_TYPE,
    EM_A_NET_ACCESSCTLCARD_AUTHORITY,
)
from NetSDK.SDK_Struct import (
    NET_RECORDSET_ACCESS_CTL_CARD,
    NET_CTRL_RECORDSET_INSERT_PARAM,
    NET_CTRL_RECORDSET_PARAM,
    NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION,
    NET_IN_FIND_RECORD_PARAM,
    NET_OUT_FIND_RECORD_PARAM,
    NET_IN_FIND_NEXT_RECORD_PARAM,
    NET_OUT_FIND_NEXT_RECORD_PARAM,
)


def main() -> None:
    required = {
        "NET_RECORDSET_ACCESS_CTL_CARD": NET_RECORDSET_ACCESS_CTL_CARD,
        "NET_CTRL_RECORDSET_INSERT_PARAM": NET_CTRL_RECORDSET_INSERT_PARAM,
        "NET_CTRL_RECORDSET_PARAM": NET_CTRL_RECORDSET_PARAM,
        "NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION": NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION,
        "NET_IN_FIND_RECORD_PARAM": NET_IN_FIND_RECORD_PARAM,
        "NET_OUT_FIND_RECORD_PARAM": NET_OUT_FIND_RECORD_PARAM,
        "NET_IN_FIND_NEXT_RECORD_PARAM": NET_IN_FIND_NEXT_RECORD_PARAM,
        "NET_OUT_FIND_NEXT_RECORD_PARAM": NET_OUT_FIND_NEXT_RECORD_PARAM,
    }
    missing_fields = {
        "NET_RECORDSET_ACCESS_CTL_CARD": {
            "szCardNo", "szUserID", "emStatus", "emType", "nDoorNum",
            "sznDoors", "nTimeSectionNum", "sznTimeSectionNo",
            "stuValidStartTime", "stuValidEndTime", "bIsValid", "szCardName",
            "bPersonStatus", "emAuthority",
        }
    }

    print("Dahua NetSDK IC-card definitions:")
    for name, structure in required.items():
        print(f"  {name}: {sizeof(structure)} bytes")

    for name, names in missing_fields.items():
        fields = {field[0] for field in required[name]._fields_}
        missing = names - fields
        if missing:
            raise SystemExit(f"FAIL: {name} missing fields: {', '.join(sorted(missing))}")

    expected = {
        "RECORDSET_INSERT": 256,
        "RECORDSET_UPDATE": 257,
        "RECORDSET_REMOVE": 258,
    }
    for name, value in expected.items():
        actual = int(getattr(CtrlType, name))
        if actual != value:
            raise SystemExit(f"FAIL: CtrlType.{name} expected {value}, got {actual}")
        print(f"  CtrlType.{name} = {actual}")

    if int(EM_NET_RECORD_TYPE.ACCESSCTLCARD) != 4:
        raise SystemExit("FAIL: EM_NET_RECORD_TYPE.ACCESSCTLCARD is not 4")
    print("  EM_NET_RECORD_TYPE.ACCESSCTLCARD = 4")
    print(f"  Normal card state = {int(EM_A_NET_ACCESSCTLCARD_STATE.NET_ACCESSCTLCARD_STATE_NORMAL)}")
    print(f"  General card type = {int(EM_A_NET_ACCESSCTLCARD_TYPE.NET_ACCESSCTLCARD_TYPE_GENERAL)}")
    print(f"  Customer authority = {int(EM_A_NET_ACCESSCTLCARD_AUTHORITY.NET_ACCESSCTLCARD_AUTHORITY_CUSTOMER)}")
    print("PASS: the installed Python wheel exposes the IC-card CRUD structures/enums.")
    print("NOTE: this does not test native DLL loading or the physical controller.")


if __name__ == "__main__":
    main()
