from __future__ import annotations

from ctypes import POINTER, c_int, c_void_p, cast, pointer, sizeof
from datetime import date
from functools import wraps
import threading
from typing import Any, Callable

from app.services.device_sessions import sessions


class AccessCardSDKError(RuntimeError):
    pass


_CARD_TYPES = {"general": 0, "vip": 1, "guest": 2}
_CARD_TYPE_NAMES = {value: key for key, value in _CARD_TYPES.items()}


def _decode(raw: Any) -> str:
    if raw is None:
        return ""
    try:
        return bytes(raw).split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
    except Exception:
        return str(raw).strip()


def _set_time(target: Any, value: date | None) -> None:
    if value is None:
        return
    target.dwYear = value.year
    target.dwMonth = value.month
    target.dwDay = value.day
    target.dwHour = 0
    target.dwMinute = 0
    target.dwSecond = 0


def _per_device_serialized(method: Callable):
    """Serialize read/modify/write record-set operations per controller."""
    @wraps(method)
    def wrapper(self, device_id: int, *args, **kwargs):
        with self._lock_for(device_id):
            return method(self, device_id, *args, **kwargs)
    return wrapper


def _read_time(value: Any) -> date | None:
    try:
        year, month, day = int(value.dwYear), int(value.dwMonth), int(value.dwDay)
        if not year or not month or not day:
            return None
        return date(year, month, day)
    except Exception:
        return None


class DahuaAccessCardService:
    """NetSDK access-card operations for first-generation access controllers.

    IC/MIFARE is represented by the hexadecimal card UID stored in szCardNo.
    The SDK structure marks szUserID as unsupported on some controllers, so the
    central Person record remains authoritative and szCardName is copied to the
    device as the display name.
    """

    def __init__(self) -> None:
        self._device_sdk = sessions.sdk
        self._locks_guard = threading.Lock()
        self._device_locks: dict[int, threading.RLock] = {}

    def _lock_for(self, device_id: int):
        with self._locks_guard:
            return self._device_locks.setdefault(int(device_id), threading.RLock())

    def _imports(self):
        try:
            from NetSDK.SDK_Enum import (
                CtrlType,
                EM_NET_RECORD_TYPE,
                EM_A_NET_ACCESSCTLCARD_STATE,
                EM_A_NET_ACCESSCTLCARD_TYPE,
                EM_A_NET_ACCESSCTLCARD_AUTHORITY,
            )
            from NetSDK.SDK_Struct import (
                NET_RECORDSET_ACCESS_CTL_CARD,
                NET_CTRL_RECORDSET_INSERT_IN,
                NET_CTRL_RECORDSET_INSERT_OUT,
                NET_CTRL_RECORDSET_INSERT_PARAM,
                NET_CTRL_RECORDSET_PARAM,
                NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION,
                NET_IN_FIND_RECORD_PARAM,
                NET_OUT_FIND_RECORD_PARAM,
                NET_IN_FIND_NEXT_RECORD_PARAM,
                NET_OUT_FIND_NEXT_RECORD_PARAM,
            )
            return {
                "CtrlType": CtrlType,
                "RecordType": EM_NET_RECORD_TYPE,
                "CardState": EM_A_NET_ACCESSCTLCARD_STATE,
                "CardType": EM_A_NET_ACCESSCTLCARD_TYPE,
                "Authority": EM_A_NET_ACCESSCTLCARD_AUTHORITY,
                "CardRecord": NET_RECORDSET_ACCESS_CTL_CARD,
                "InsertIn": NET_CTRL_RECORDSET_INSERT_IN,
                "InsertOut": NET_CTRL_RECORDSET_INSERT_OUT,
                "InsertParam": NET_CTRL_RECORDSET_INSERT_PARAM,
                "RecordSetParam": NET_CTRL_RECORDSET_PARAM,
                "FindCondition": NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION,
                "FindIn": NET_IN_FIND_RECORD_PARAM,
                "FindOut": NET_OUT_FIND_RECORD_PARAM,
                "FindNextIn": NET_IN_FIND_NEXT_RECORD_PARAM,
                "FindNextOut": NET_OUT_FIND_NEXT_RECORD_PARAM,
            }
        except Exception as exc:
            raise AccessCardSDKError(
                "Could not import the required access-card structures from your Dahua NetSDK wheel: "
                f"{exc}"
            ) from exc

    @staticmethod
    def _session_handle(device_id: int) -> int:
        session = sessions.get_session(device_id)
        if session is None:
            raise AccessCardSDKError(
                "Device has no active NetSDK session. Reconnect it using POST /devices/{device_id}/connect."
            )
        return int(session.handle)

    @staticmethod
    def _make_record(api: dict[str, Any], *, card_number: str, card_name: str,
                     card_type: int, is_valid: bool, valid_from: date,
                     valid_until: date, door_indices: list[int],
                     time_section_indices: list[int]):
        from ctypes import sizeof
        CardRecord = api["CardRecord"]
        record = CardRecord()
        record.dwSize = sizeof(CardRecord)
        encoded_name = card_name.encode("utf-8")
        if len(encoded_name) > 63:
            raise AccessCardSDKError("card_name must fit within 63 UTF-8 bytes for the controller record.")
        record.szCardNo = card_number.upper().encode("ascii")
        record.szCardName = encoded_name
        # This legacy controller record's szUserID is documented as unsupported
        # on some devices. Keep person_code in the central database.
        record.emStatus = int(api["CardState"].NET_ACCESSCTLCARD_STATE_NORMAL)
        type_map = {
            0: api["CardType"].NET_ACCESSCTLCARD_TYPE_GENERAL,
            1: api["CardType"].NET_ACCESSCTLCARD_TYPE_VIP,
            2: api["CardType"].NET_ACCESSCTLCARD_TYPE_GUEST,
        }
        record.emType = int(type_map[card_type])
        record.bIsValid = bool(is_valid)
        record.bPersonStatus = bool(is_valid)
        record.emAuthority = int(api["Authority"].NET_ACCESSCTLCARD_AUTHORITY_CUSTOMER)
        record.nDoorNum = len(door_indices)
        for index, door in enumerate(door_indices):
            record.sznDoors[index] = int(door)
        record.nTimeSectionNum = len(time_section_indices)
        for index, section in enumerate(time_section_indices):
            record.sznTimeSectionNo[index] = int(section)
        # Use legacy door/time arrays for compatibility with ASI1201E firmware.
        record.bNewDoor = False
        _set_time(record.stuValidStartTime, valid_from)
        _set_time(record.stuValidEndTime, valid_until)
        return record

    @_per_device_serialized
    def list_device_cards(self, device_id: int, card_number: str | None = None) -> list[dict[str, Any]]:
        from ctypes import cast, c_void_p, POINTER, sizeof
        api = self._imports()
        handle = self._session_handle(device_id)
        condition = api["FindCondition"]()
        condition.dwSize = sizeof(api["FindCondition"])
        if card_number:
            condition.szCardNo = card_number.upper().encode("ascii")
            condition.abCardNo = True

        find_in = api["FindIn"]()
        find_in.dwSize = sizeof(api["FindIn"])
        find_in.emType = int(api["RecordType"].ACCESSCTLCARD)
        find_in.pQueryCondition = cast(pointer(condition), c_void_p)
        find_out = api["FindOut"]()
        find_out.dwSize = sizeof(api["FindOut"])

        client = self._device_sdk._client
        if not client.FindRecord(handle, find_in, find_out, 5000):
            raise AccessCardSDKError(f"Dahua FindRecord failed: {client.GetLastErrorMessage()}")

        find_handle = int(getattr(find_out.lFindeHandle, "value", find_out.lFindeHandle))
        results: list[dict[str, Any]] = []
        try:
            batch_size = 20
            while True:
                find_next_in = api["FindNextIn"]()
                find_next_in.dwSize = sizeof(api["FindNextIn"])
                find_next_in.lFindeHandle = find_handle
                find_next_in.nFileCount = batch_size

                find_next_out = api["FindNextOut"]()
                find_next_out.dwSize = sizeof(api["FindNextOut"])
                find_next_out.nMaxRecordNum = batch_size
                buffer = (api["CardRecord"] * batch_size)()
                for item in buffer:
                    item.dwSize = sizeof(api["CardRecord"])
                find_next_out.pRecordList = cast(buffer, c_void_p)

                if not client.FindNextRecord(find_next_in, find_next_out, 5000):
                    raise AccessCardSDKError(f"Dahua FindNextRecord failed: {client.GetLastErrorMessage()}")
                count = int(find_next_out.nRetRecordNum)
                if count < 0 or count > batch_size:
                    raise AccessCardSDKError(f"Dahua returned an invalid card record count: {count}")
                records = cast(
                    find_next_out.pRecordList,
                    POINTER(api["CardRecord"] * batch_size),
                ).contents
                for index in range(count):
                    row = records[index]
                    results.append({
                        "record_number": int(row.nRecNo),
                        "card_number": _decode(row.szCardNo),
                        "card_name": _decode(row.szCardName),
                        "card_status": int(row.emStatus),
                        "card_type": int(row.emType),
                        "is_valid": bool(row.bIsValid),
                        "valid_from": _read_time(row.stuValidStartTime),
                        "valid_until": _read_time(row.stuValidEndTime),
                        "door_indices": [int(row.sznDoors[i]) for i in range(min(int(row.nDoorNum), 32))],
                        "time_section_indices": [int(row.sznTimeSectionNo[i]) for i in range(min(int(row.nTimeSectionNum), 32))],
                        "device_user_id": _decode(row.szUserID) or None,
                    })
                if count < batch_size:
                    break
        finally:
            client.FindRecordClose(find_handle)
        return results

    @_per_device_serialized
    def add_device_card(self, device_id: int, *, card_number: str, card_name: str,
                        card_type: int, is_valid: bool, valid_from: date,
                        valid_until: date, door_indices: list[int],
                        time_section_indices: list[int]) -> int:
        from ctypes import cast, c_void_p, pointer, sizeof
        api = self._imports()
        handle = self._session_handle(device_id)
        duplicate = self.list_device_cards(device_id, card_number=card_number)
        if duplicate:
            raise AccessCardSDKError(f"Card {card_number} already exists on the controller.")
        record = self._make_record(
            api, card_number=card_number, card_name=card_name, card_type=card_type,
            is_valid=is_valid, valid_from=valid_from, valid_until=valid_until,
            door_indices=door_indices, time_section_indices=time_section_indices,
        )
        insert_param = api["InsertParam"]()
        insert_param.dwSize = sizeof(api["InsertParam"])
        insert_param.stuCtrlRecordSetInfo.dwSize = sizeof(api["InsertIn"])
        insert_param.stuCtrlRecordSetInfo.emType = int(api["RecordType"].ACCESSCTLCARD)
        insert_param.stuCtrlRecordSetInfo.pBuf = cast(pointer(record), c_void_p)
        insert_param.stuCtrlRecordSetInfo.nBufLen = sizeof(api["CardRecord"])
        insert_param.stuCtrlRecordSetResult.dwSize = sizeof(api["InsertOut"])
        client = self._device_sdk._client
        if not client.ControlDevice(handle, api["CtrlType"].RECORDSET_INSERT, insert_param, 5000):
            raise AccessCardSDKError(f"Dahua card insert failed: {client.GetLastErrorMessage()}")
        return int(insert_param.stuCtrlRecordSetResult.nRecNo)

    @_per_device_serialized
    def update_device_card(self, device_id: int, record_number: int, *, original_card_number: str, card_number: str,
                           card_name: str, card_type: int, is_valid: bool,
                           valid_from: date, valid_until: date,
                           door_indices: list[int], time_section_indices: list[int]) -> None:
        from ctypes import cast, c_void_p, pointer, sizeof
        api = self._imports()
        handle = self._session_handle(device_id)
        # Refuse changing a UID to one already present on the physical device.
        duplicate_rows = self.list_device_cards(device_id, card_number=card_number)
        if any(int(item["record_number"]) != int(record_number) for item in duplicate_rows):
            raise AccessCardSDKError(f"Card {card_number} already exists on the controller.")
        # Search using the original UID so changing the UID does not lose the record.
        current_rows = self._find_native_records(device_id, original_card_number)
        if not current_rows:
            raise AccessCardSDKError(f"Could not reload native card record {record_number}.")
        # Keep the native result buffer alive until ControlDevice returns. The
        # card structure contains pointer fields (for extended floor data), so
        # copying it and releasing the source buffer could leave dangling pointers.
        record, record_buffer = current_rows[0]
        if int(record.nRecNo) != int(record_number):
            raise AccessCardSDKError("The controller returned a different record number; update cancelled.")
        encoded_name = card_name.encode("utf-8")
        if len(encoded_name) > 63:
            raise AccessCardSDKError("card_name must fit within 63 UTF-8 bytes for the controller record.")
        record.szCardNo = card_number.upper().encode("ascii")
        record.szCardName = encoded_name
        record.emStatus = int(api["CardState"].NET_ACCESSCTLCARD_STATE_NORMAL)
        record.emType = int({
            0: api["CardType"].NET_ACCESSCTLCARD_TYPE_GENERAL,
            1: api["CardType"].NET_ACCESSCTLCARD_TYPE_VIP,
            2: api["CardType"].NET_ACCESSCTLCARD_TYPE_GUEST,
        }[card_type])
        record.bIsValid = bool(is_valid)
        record.bPersonStatus = bool(is_valid)
        record.nDoorNum = len(door_indices)
        for idx, door in enumerate(door_indices):
            record.sznDoors[idx] = int(door)
        record.nTimeSectionNum = len(time_section_indices)
        for idx, section in enumerate(time_section_indices):
            record.sznTimeSectionNo[idx] = int(section)
        record.bNewDoor = False
        _set_time(record.stuValidStartTime, valid_from)
        _set_time(record.stuValidEndTime, valid_until)

        param = api["RecordSetParam"]()
        param.dwSize = sizeof(api["RecordSetParam"])
        param.emType = int(api["RecordType"].ACCESSCTLCARD)
        param.pBuf = cast(pointer(record), c_void_p)
        param.nBufLen = sizeof(api["CardRecord"])
        client = self._device_sdk._client
        if not client.ControlDevice(handle, api["CtrlType"].RECORDSET_UPDATE, param, 5000):
            raise AccessCardSDKError(f"Dahua card update failed: {client.GetLastErrorMessage()}")

    def _find_native_records(self, device_id: int, card_number: str):
        from ctypes import cast, c_void_p, pointer, sizeof, POINTER
        api = self._imports()
        handle = self._session_handle(device_id)
        condition = api["FindCondition"]()
        condition.dwSize = sizeof(api["FindCondition"])
        condition.szCardNo = card_number.upper().encode("ascii")
        condition.abCardNo = True
        find_in = api["FindIn"]()
        find_in.dwSize = sizeof(api["FindIn"])
        find_in.emType = int(api["RecordType"].ACCESSCTLCARD)
        find_in.pQueryCondition = cast(pointer(condition), c_void_p)
        find_out = api["FindOut"]()
        find_out.dwSize = sizeof(api["FindOut"])
        client = self._device_sdk._client
        if not client.FindRecord(handle, find_in, find_out, 5000):
            raise AccessCardSDKError(f"Dahua FindRecord failed: {client.GetLastErrorMessage()}")
        find_handle = int(getattr(find_out.lFindeHandle, "value", find_out.lFindeHandle))
        found = []
        # Keep `buff` alive alongside each structure until the caller finishes
        # the update operation. See update_device_card() above.
        try:
            size = 10
            ni = api["FindNextIn"](); ni.dwSize = sizeof(api["FindNextIn"]); ni.lFindeHandle = find_handle; ni.nFileCount = size
            no = api["FindNextOut"](); no.dwSize = sizeof(api["FindNextOut"]); no.nMaxRecordNum = size
            buff = (api["CardRecord"] * size)()
            for item in buff:
                item.dwSize = sizeof(api["CardRecord"])
            no.pRecordList = cast(buff, c_void_p)
            if not client.FindNextRecord(ni, no, 5000):
                raise AccessCardSDKError(f"Dahua FindNextRecord failed: {client.GetLastErrorMessage()}")
            count = int(no.nRetRecordNum)
            rows = cast(no.pRecordList, POINTER(api["CardRecord"] * size)).contents
            for i in range(min(count, size)):
                found.append((rows[i], buff))
        finally:
            client.FindRecordClose(find_handle)
        return found

    @_per_device_serialized
    def delete_device_card(self, device_id: int, record_number: int) -> None:
        from ctypes import cast, c_void_p, c_int, pointer, sizeof
        api = self._imports()
        handle = self._session_handle(device_id)
        record_no = c_int(int(record_number))
        param = api["RecordSetParam"]()
        param.dwSize = sizeof(api["RecordSetParam"])
        param.emType = int(api["RecordType"].ACCESSCTLCARD)
        param.pBuf = cast(pointer(record_no), c_void_p)
        param.nBufLen = sizeof(c_int)
        client = self._device_sdk._client
        if not client.ControlDevice(handle, api["CtrlType"].RECORDSET_REMOVE, param, 5000):
            raise AccessCardSDKError(f"Dahua card delete failed: {client.GetLastErrorMessage()}")


access_cards = DahuaAccessCardService()
