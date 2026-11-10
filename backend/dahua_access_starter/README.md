# Dahua Access Control API Starter

FastAPI backend for Dahua ASI1201E access controllers using the Dahua NetSDK Python wheel.

## Current modules

- Device registration, connection/disconnection and automatic TCP health monitoring.
- Central personnel records (`/persons`).
- IC/MIFARE card assignment to a specific controller (`/devices/{device_id}/cards`).
- Native controller card query (`/devices/{device_id}/cards/device-records`).
- Native controller card insert, update and remove through NetSDK record-set operations.
- Person-to-card assignment lookup across registered controllers (`/persons/{person_id}/cards`).

## IC card compatibility

This phase is for the base **DHI-ASI1201E 13.56 MHz IC/MIFARE** reader, not the 125 kHz `ASI1201E-D` variant. The card UID is stored and sent as a hexadecimal string such as `FB66983B`; it is intentionally not converted to an integer so leading zeroes are preserved.

The installed NetSDK 3.060 Python wheel contains the relevant native definitions:

- `NET_RECORDSET_ACCESS_CTL_CARD`
- `NET_CTRL_RECORDSET_INSERT_PARAM`
- `NET_CTRL_RECORDSET_PARAM`
- `NET_A_FIND_RECORD_ACCESSCTLCARD_CONDITION`
- `NET_IN_FIND_RECORD_PARAM` / `NET_OUT_FIND_RECORD_PARAM`
- `NET_IN_FIND_NEXT_RECORD_PARAM` / `NET_OUT_FIND_NEXT_RECORD_PARAM`

The access-card CRUD implementation uses:

- `NetClient.ControlDevice(..., CtrlType.RECORDSET_INSERT, ...)`
- `NetClient.ControlDevice(..., CtrlType.RECORDSET_UPDATE, ...)`
- `NetClient.ControlDevice(..., CtrlType.RECORDSET_REMOVE, ...)`
- `NetClient.FindRecord`, `FindNextRecord`, and `FindRecordClose` with `EM_NET_RECORD_TYPE.ACCESSCTLCARD`

The SDK's `NET_RECORDSET_ACCESS_CTL_CARD` declaration marks `szUserID` as unsupported on this legacy record format. Therefore `Person` is the central application record, while `szCardName`, card UID, validity, door indexes and time-section indexes are synchronized to the controller. The application keeps the `person_id` ↔ device-card assignment mapping. Creating/updating a `/persons` record changes the central database only; assigning/updating a `/devices/{device_id}/cards` record changes the physical controller. If a person's name changes, update the card's `card_name` separately when you want the controller display name changed.

## Important permission/index note

For initial ASI1201E testing, the card schema defaults to Door index `0` and time-section index `0` (typically Door 1 / the first device time section). Confirm these indexes against the controller's actual Door Parameters and time-template configuration before production use. The card can be registered successfully while still being denied access if the selected door/time schedule is not valid.

The SDK card structure stores validity as `NET_TIME` and its comments state that this record does not support hour/minute/second precision. The API therefore accepts dates only. Exact access windows belong in the device time-section configuration, which is a later module.

## Verify the IC-card SDK structures

Run this after the wheel is installed in the existing venv:

```powershell
..\venv\Scripts\python.exe tools\verify_card_sdk.py
```

The verifier checks the exact enum values, ctypes field names and structure sizes used by this module. It does not initialize the native DLL or modify the physical controller.

## Install / run on the existing Windows venv

From `C:\Dahua-Standalone\dahua_access_starter`:

```powershell
..\venv\Scripts\python.exe -m pip install -r requirements.txt
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`.

Keep the existing `data` folder, `device_secret.key`, SQLite database and `venv`. New `persons` and `access_cards` tables are created automatically on startup; existing device data is preserved.

## API workflow

### 1. Create a central person

`POST /persons`

```json
{
  "person_code": "EMP-0001",
  "name": "Sahil",
  "department": "IT",
  "phone": "03000000000",
  "email": "sahil@example.com"
}
```

### 2. Assign an IC card to that person on controller ID 2

`POST /devices/2/cards`

```json
{
  "person_id": 1,
  "card_number": "FB66983B",
  "card_type": "general",
  "is_valid": true,
  "valid_from": "2026-11-10",
  "valid_until": "2036-11-09",
  "door_indices": [0],
  "time_section_indices": [0]
}
```

If `card_name` is omitted, the person's name is sent as the device card name.

### 3. List app assignments

`GET /devices/2/cards`

### 4. Read card records directly from controller

`GET /devices/2/cards/device-records`

### 5. Update a controller card

`PUT /devices/2/cards/{assignment_id}`

```json
{
  "card_name": "Sahil Ahmed",
  "is_valid": true,
  "valid_until": "2036-11-09"
}
```

### 6. Delete a controller card assignment

`DELETE /devices/2/cards/{assignment_id}`

This removes the card record from the controller and then removes the local assignment. It does not delete the central person record if that person is assigned to other controllers.

### 7. Person CRUD

- `GET /persons`
- `GET /persons/{person_id}`
- `PUT /persons/{person_id}`
- `GET /persons/{person_id}/cards` (all controller card assignments for this person)
- `DELETE /persons/{person_id}`

A person with active card assignments cannot be deleted. Remove its card assignments first to avoid orphaning card records on devices.

## Testing limitations

Python syntax, route imports, schema validation, SQLite model creation, and the NetSDK card ctypes structures/enums were checked against the supplied NetSDK 3.060 Python wheel. A mocked SDK test passed insert/list/update/delete pointer handling. The Windows-only Dahua native SDK DLLs are not available on this build runner, so **native insert/update/delete/query must still be tested on the Windows PC against the ASI1201E** before treating the hardware operations as device-verified. Start with one test IC card and verify the controller's existing cards remain intact.

Do not use any clear-all card command. This module intentionally has no endpoint to clear all cards.

## Production scaling

This is still a development starter. For more than 1,000 controllers, run device operations through a queued, per-device serialized worker, shard sessions and monitoring, add authentication/authorization and audit logs, and load-test SDK session/resource limits. Do not run multiple Uvicorn workers that each independently initialize and own the same NetSDK sessions.

## Import existing SmartPSS Lite / controller card records

Use `POST /devices/{device_id}/cards/import` to import controller card records
into the central application database. New device-only cards create minimal
placeholder people (`profile_source=device_import`); no person is matched by name.
Repeated imports are idempotent for the same device/card pair.
