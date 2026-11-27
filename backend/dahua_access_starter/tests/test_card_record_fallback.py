"""A card whose stored controller record number is wrong can still be found by its UID.

Site case: card FB66983B was stored with record number -77162437 (the UID read as int32),
so revoke failed with "Could not reload native card record". Uses the real NetSDK
structures and a fake controller; no device is contacted.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("NetSDK")

from app.services.access_cards import AccessCardSDKError, access_cards  # noqa: E402


def _fake_controller(monkeypatch, records: list[tuple[int, str]]):
    api = access_cards._imports()

    def find_next(_inp, out, _timeout):
        rows = ctypes.cast(out.pRecordList, ctypes.POINTER(api["CardRecord"] * 20)).contents
        for index, (rec_no, uid) in enumerate(records):
            rows[index].nRecNo = rec_no
            rows[index].szCardNo = uid.encode("ascii")
        out.nRetRecordNum = len(records)
        return True

    client = SimpleNamespace(
        FindRecord=lambda *_a: True,
        FindNextRecord=find_next,
        FindRecordClose=lambda *_a: True,
        GetLastErrorMessage=lambda: "fake",
    )
    monkeypatch.setattr(access_cards, "_device_sdk", SimpleNamespace(_client=client))
    monkeypatch.setattr(access_cards, "_session_handle", lambda _device_id: 1)


def test_wrong_record_number_falls_back_to_the_card_uid(monkeypatch):
    _fake_controller(monkeypatch, [(5, "11223344"), (7, "FB66983B")])
    found = access_cards._find_native_records(1, "FB66983B", -77162437)
    assert [int(row.nRecNo) for row, _ in found] == [7]


def test_record_number_pointing_at_another_card_is_still_refused(monkeypatch):
    _fake_controller(monkeypatch, [(5, "11223344"), (7, "FB66983B")])
    with pytest.raises(AccessCardSDKError):
        access_cards._find_native_records(1, "FB66983B", 5)


def test_duplicate_uid_on_controller_is_not_guessed(monkeypatch):
    _fake_controller(monkeypatch, [(7, "FB66983B"), (9, "FB66983B")])
    assert access_cards._find_native_records(1, "FB66983B", -77162437) == []
