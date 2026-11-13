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
