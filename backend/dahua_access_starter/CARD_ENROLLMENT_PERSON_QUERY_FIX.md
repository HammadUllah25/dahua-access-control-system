# Superseded: personnel-query buffer experiment

This diagnostic note describes an earlier experiment intended to make `OperateAccessUserService(GET)` work. That lookup returned SDK error `0x00000015` on the reported ASI1201E installation and is not required for the ASI1201E scan-to-enroll workflow.

## Current behavior

The confirmation endpoint now:

1. Claims a captured RFID enrollment session.
2. Validates the captured hexadecimal card UID.
3. Calls the same `_write_card_assignment()` path used by `POST /devices/{device_id}/cards`.
4. Uses `CLIENT_ControlDevice` with `RECORDSET_INSERT` and `NET_RECORDSET_ACCESS_CTL_CARD` to write the card record.
5. Saves the application-side relationship between the selected person and the card in SQLite.

The backend does not call `add_device_user()`, `get_device_user_records()`, or `delete_device_user()` during this workflow. The optional personnel-service methods remain in the codebase for other compatible controller models but are not prerequisites for ASI1201E card assignment.

## Hardware verification still required

The native NetSDK DLLs cannot be exercised in this Linux build environment. On the Windows PC connected to the ASI1201E, test with one spare card after backing up the controller/application data. Confirm that the card appears in `GET /devices/{device_id}/cards/device-records`, that its application link appears in `GET /devices/{device_id}/cards`, and then verify the physical door behavior. A successful local/mocked test is not proof of controller firmware behavior.
