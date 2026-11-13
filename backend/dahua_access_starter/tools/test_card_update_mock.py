"""Offline regression test for the ASI1201E card update lookup path.

This test uses the bundled NetSDK ctypes declarations and a fake native client.
It does NOT connect to or modify a physical Dahua controller.
Run from the project root with the project's Python environment:
    python tools/test_card_update_mock.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from ctypes import POINTER, cast, sizeof

ROOT = Path(__file__).resolve().parents[1]
WHEEL = ROOT / "vendor" / "NetSDK-2.0.0.1-py3-none-win_amd64.whl"
if WHEEL.exists():
    sys.path.insert(0, str(WHEEL))

from NetSDK.SDK_Enum import CtrlType
from NetSDK.SDK_Struct import NET_RECORDSET_ACCESS_CTL_CARD
from app.services.access_cards import access_cards


class FakeNativeClient:
    def __init__(self) -> None:
        self.find_record_calls = 0
        self.find_next_calls = 0
        self.find_close_calls = 0
        self.update_calls = 0
        self.record_no = -77162437
        self.card_number = "FB66983B"
        self.updated_record: NET_RECORDSET_ACCESS_CTL_CARD | None = None
        self.condition_flags: tuple[bool, bool, bool] | None = None
        self.find_out_size_ok = False

    def FindRecord(self, _handle, find_in, find_out, _timeout):
        self.find_record_calls += 1
        from NetSDK.SDK_Struct import NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION

        condition = cast(
            find_in.pQueryCondition,
            POINTER(NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION),
        ).contents
        self.condition_flags = (
            bool(condition.abCardNo),
            bool(condition.abUserID),
            bool(condition.abIsValid),
        )
        from NetSDK.SDK_Struct import NET_OUT_FIND_RECORD_PARAM
        self.find_out_size_ok = int(find_out.dwSize) == sizeof(NET_OUT_FIND_RECORD_PARAM)
        find_out.lFindeHandle = 12345
        return True

    def FindNextRecord(self, _find_next_in, find_next_out, _timeout):
        self.find_next_calls += 1
        rows = cast(
            find_next_out.pRecordList,
            POINTER(NET_RECORDSET_ACCESS_CTL_CARD * find_next_out.nMaxRecordNum),
        ).contents
        rows[0].dwSize = sizeof(NET_RECORDSET_ACCESS_CTL_CARD)
        rows[0].nRecNo = self.record_no
        rows[0].szCardNo = self.card_number.encode("ascii")
        rows[0].szCardName = b"Original card"
        rows[0].emStatus = 0
        rows[0].emType = 0
        rows[0].bIsValid = True
        rows[0].bPersonStatus = True
        rows[0].nDoorNum = 1
        rows[0].sznDoors[0] = 0
        rows[0].nTimeSectionNum = 1
        rows[0].sznTimeSectionNo[0] = 0
        find_next_out.nRetRecordNum = 1
        return True

    def FindRecordClose(self, _find_handle):
        self.find_close_calls += 1
        return True

    def ControlDevice(self, _handle, operation, param, _timeout):
        assert int(operation) == int(CtrlType.RECORDSET_UPDATE)
        self.update_calls += 1
        self.updated_record = cast(
            param.pBuf,
            POINTER(NET_RECORDSET_ACCESS_CTL_CARD),
        ).contents
        assert int(param.nBufLen) == sizeof(NET_RECORDSET_ACCESS_CTL_CARD)
        return True

    @staticmethod
    def GetLastErrorMessage():
        return "mock error"


def main() -> None:
    fake = FakeNativeClient()
    original_client = access_cards._device_sdk._client
    original_session_handle = access_cards._session_handle
    try:
        access_cards._device_sdk._client = fake
        access_cards._session_handle = lambda _device_id: 456
        access_cards.update_device_card(
            1,
            fake.record_no,
            original_card_number=fake.card_number,
            card_number=fake.card_number,
            card_name="Hammad RFID Card - Updated",
            card_type=0,
            is_valid=False,
            valid_from=date(2026, 11, 12),
            valid_until=date(2037, 12, 31),
            door_indices=[0],
            time_section_indices=[0],
        )

        assert fake.find_record_calls == 1, "Expected exactly one FindRecord call"
        assert fake.condition_flags == (True, False, False), "FindRecord should target the original card UID"
        assert fake.find_out_size_ok, "NET_OUT_FIND_RECORD_PARAM.dwSize must be initialized"
        assert fake.find_next_calls == 1
        assert fake.find_close_calls == 1
        assert fake.update_calls == 1, "Expected one RECORDSET_UPDATE call"
        assert fake.updated_record is not None
        assert int(fake.updated_record.nRecNo) == fake.record_no
        assert fake.updated_record.szCardNo.decode("ascii") == fake.card_number
        assert fake.updated_record.szCardName.decode("utf-8") == "Hammad RFID Card - Updated"
        assert bool(fake.updated_record.bIsValid) is False
        assert bool(fake.updated_record.bPersonStatus) is False
        print("PASS: update initializes FindRecord output size, preserves record number, and calls RECORDSET_UPDATE.")
        print("NOTE: this is an offline mock; it does not prove the ASI1201E firmware accepts card updates.")
    finally:
        access_cards._device_sdk._client = original_client
        access_cards._session_handle = original_session_handle


if __name__ == "__main__":
    main()
