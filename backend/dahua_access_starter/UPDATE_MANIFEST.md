# ASI1201E card enrollment update

## Changed behavior

- Reworked `POST /devices/{device_id}/card-enrollments/{session_token}/confirm` to use the existing card-record assignment function directly.
- The confirmation flow no longer calls `OperateAccessUserService(GET/INSERT/REMOVE)` and no longer creates a separate controller personnel profile.
- The selected central application person is linked to the captured card UID in SQLite.
- Removed `user_password` from the confirmation request schema because the ASI1201E card-only workflow does not submit a separate personnel credential.
- Confirmation response now returns `person_id` and the saved `card` assignment; it no longer implies a device-side personnel UserID exists.
- The direct personnel-profile endpoint returns HTTP 501 for ASI1201E-family models, and native card-record listing skips the optional personnel-service lookup on these models.
- Corrected the Windows setup scripts to create a local `.venv` and install the provided Dahua NetSDK wheel into that environment.
- Added an offline confirmation-flow regression test and a setup diagnostic.

## Preserved behavior

Device discovery/initialization, login/session management, alarm listening, scan-to-enroll capture, device monitoring, events, people CRUD, direct card CRUD, card import, and existing SQLite model/schema behavior remain in place.

## Data safety

The release ZIP intentionally excludes `data/dahua_access.db`, `data/device_secret.key`, `.env`, and any virtual environment. Keep/restore your local database and encryption key. Losing `device_secret.key` prevents decrypting stored device passwords.

## Verification boundary

Python compilation, API import, schema validation, and the offline confirmation-flow regression test run without a controller. The physical Dahua DLL/API call cannot be tested in this environment; a one-card test against the ASI1201E is still required before production use.

## Card-update lookup correction

- Fixed `_find_native_records()` to initialize `NET_OUT_FIND_RECORD_PARAM.dwSize` before `FindRecord`. The previous method omitted this required SDK structure-size field, although the normal card-list query initialized it.
- The update path now skips the duplicate-UID lookup when the card UID is unchanged, avoiding an unnecessary native query. If the UID changes, the duplicate check remains in place.
- Added `tools/test_card_update_mock.py`, which uses the bundled SDK ctypes declarations and a fake client to check `dwSize`, original record-number preservation, and the `RECORDSET_UPDATE` call. This test does not connect to a physical device.
- No database, device key, environment file, or installed virtual environment is included in the patched ZIP.

## Verification boundary

The lookup initialization fix is covered by an offline mock test. The real ASI1201E must still be tested using a spare card: the mock cannot establish whether this firmware accepts `RECORDSET_UPDATE` or whether setting `bIsValid=False` revokes physical access.

## Station-card recovery and legacy-card adoption update

- Added `POST /stations/{station_id}/cards/adopt-existing` to convert a pre-existing person-based `AccessCard` row into a station `USER` or `STAFF` assignment without touching the physical controller.
- The adoption route preserves the legacy Person and AccessCard rows, defaults `USER` to billable and `STAFF` to non-billable, clears the old controller record number, and marks the new station assignment as requiring reprovisioning.
- The existing `POST /devices/{device_id}/reprovision` endpoint restores the adopted station assignments after an administrator confirms a factory reset.
- Added a guard against repeating a confirmed restore when a prior attempt is running, failed, or awaiting verification; this avoids duplicate native card inserts when SDK inventory readback is unavailable.
- Added `POST /devices/{device_id}/reprovision/manual-verification` for an administrator to record SmartPSS review and successful physical scans when the device firmware does not support SDK inventory readback.
- Added an offline regression test covering preservation of legacy rows, USER/STAFF assignment, confirmed reprovision, duplicate-retry protection, and manual verification.
- Added `RECOVERY_STEPS_CURRENT_INSTALLATION.md` with exact steps for the current Station ID 1 / Device ID 1 setup. It warns not to adopt `0B56` unless it is confirmed to be a real physical card.

## Verification boundary

All route logic and the regression tests run with mocked SDK calls. This environment cannot connect to the user's Windows-hosted ASI1201E or validate the native card insert against its current firmware. The first restore must be checked in SmartPSS and with a physical card scan.


## Version 1.1.5 — ASI1201E reactivation lookup compatibility

- Updated `_find_native_records()` to use the unfiltered card inventory query already supported by the working inventory-list path. It now matches the controller record number and UID locally before updating.
- Added an offline mock regression assertion that the update lookup does not enable the unsupported card-number filter.
- This avoids the filtered `FindRecord` request that failed on the reported ASI1201E. Physical `RECORDSET_UPDATE` acceptance remains to be verified on the actual controller.
