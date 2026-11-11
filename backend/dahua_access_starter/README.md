# Dahua Access Control API Starter

FastAPI backend for Dahua ASI1201E access controllers using the Dahua NetSDK Python wheel.

## Current modules

- Device registration, connection/disconnection and automatic TCP health monitoring.
- Central personnel records (`/persons`).
- IC/MIFARE card assignment to a specific controller (`/devices/{device_id}/cards`).
- Native controller card query (`/devices/{device_id}/cards/device-records`).
- Native controller card insert, update and remove through NetSDK record-set operations.
- Person-to-card assignment lookup across registered controllers (`/persons/{person_id}/cards`).


## Factory-reset device initialization

The `/device-initialization` API initializes a factory-reset controller using the native Dahua NetSDK flow. It does **not** require Dahua ConfigTool. It uses the exact structures and callback types in the supplied NetSDK 3.060 Python wheel:

1. List the PC's IPv4 network interfaces.
2. Search the selected LAN with `StartSearchDevicesEx`.
3. Read the device MAC, initialization state, password-recovery flags, device IP/port and the local interface IP from the SDK callback.
4. Initialize the account with `InitDevAccount`, reusing the same local interface IP and the `byPwdResetWay` value returned by discovery.

### Step 1 — list local network interfaces

`GET /device-initialization/interfaces`

Use the Ethernet IPv4 address connected to the controller LAN. If it is not listed, it can be supplied directly in the discovery request.

### Step 2 — discover the factory-reset controller

`POST /device-initialization/discover`

```json
{
  "local_ip": "192.168.0.10",
  "wait_seconds": 5
}
```

`local_ip` is the PC/laptop network adapter address, not the controller IP. It must be the interface through which the controller is reachable. If `local_ip` is omitted, the API searches through detected non-loopback IPv4 interfaces.

Only devices whose initialization-state bits report `uninitialized` can be initialized. The response includes each device's `mac_address`, `local_ip`, `ip_address`, `tcp_port`, `serial_number`, `model`, and supported recovery methods.

### Step 3 — initialize the account

`POST /device-initialization/initialize`

Use the exact `mac_address` and `local_ip` returned for the selected device.

```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "local_ip": "192.168.0.10",
  "username": "admin",
  "password": "YourNewStrongPassword",
  "confirm_password": "YourNewStrongPassword",
  "cellphone": "03001234567",
  "email": "admin@example.com"
}
```

The MAC shown above is only a placeholder; use the real value returned by discovery. `cellphone` and `email` are optional and are accepted only when the device reports support for the corresponding recovery method. The API checks that the password confirmation matches and uses the SDK-reported reset flags rather than guessing them.

**Important:** account initialization changes the controller from uninitialized to initialized; it is not a read-only test and cannot be undone through this endpoint. Run it only after confirming the selected device and the new credentials. Keep this API private during setup; do not expose an unauthenticated initialization endpoint to the public internet. The API does not save the credentials in the device table automatically.

### Step 4 — register the initialized controller

After successful initialization, register it through the existing `POST /devices` endpoint using the discovered `device_ip`, `tcp_port`, and the new username/password. Registration remains separate so a controller is not assigned to the wrong petrol-pump/site record accidentally.

### Verify the installed SDK declarations

```powershell
..\venv\Scripts\python.exe tools\verify_initialization_sdk.py
```

This check validates the ctypes structures and enums without loading the native DLL or changing a controller. The mocked orchestration test can be run with `..\venv\Scripts\python.exe tools\test_initialization_mock.py` (with the NetSDK wheel installed). The native discovery/initialization calls still need to be run on the Windows PC with the ASI1201E on the same LAN. Keep the SDK installed in the existing venv; this project archive does not bundle Dahua's proprietary DLLs.

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


## Reading full controller card and person details

`GET /devices/{device_id}/cards/device-records` reads card records and, when the card record includes a controller user ID, also attempts a separate Dahua personnel lookup. The response includes `person_profile` and `person_profile_error`; a card record remains available even if the device firmware does not support the personnel lookup.

For an isolated person lookup, use `GET /devices/{device_id}/person-records/{device_user_id}`. For example, the existing card record returned user ID `101`, so test `GET /devices/2/person-records/101`.

The response now includes the SDK fields relevant to the SmartPSS Lite Basic Info and Card panels: device person ID/name/type/status, department, validity dates, usage-limit value, password-presence flag, card issue/creation timestamp, card status/type/UID, door and time-section indexes, plus additional non-secret profile/card metadata where the controller returns it.

**Credential and biometric handling:** the API never returns `szPsw`, the card password itself, or raw face-template bytes. It returns only `password_configured` and a face-template count. Face photographs/templates use a separate Dahua face service; the example SmartPSS Lite screenshot shows placeholder silhouettes rather than uploaded images.

**Date limitation:** the `NET_RECORDSET_ACCESS_CTL_CARD` structure in the supplied NetSDK exposes `stuCreateTime` (card-record creation time) but no card-record modification timestamp. The person service exposes `stuUpdateTime` for the person profile, which is returned separately as `person_profile.update_time`; it must not be presented as the card's change date.

The new personnel lookup uses `OperateAccessUserService` and is not yet verified against the physical ASI1201E in this project. Run the two GET endpoints above on the controller and share the responses; firmware support and populated fields must be confirmed on the actual device.

---

## Live Access Events (ASI1201E)

The backend registers the NetSDK message callback with `SetDVRMessCallBackEx1` during SDK initialization and starts device-specific alarm listening after a successful login with `StartListenEx`. Access-control messages are decoded from `NET_A_ALARM_ACCESS_CTL_EVENT_INFO` (`SDK_ALARM_TYPE.ALARM_ACCESS_CTL_EVENT`).

The callback copies the event fields and enqueues them. A background persistence worker writes each received event to the `access_events` table using its own SQLAlchemy database session. This keeps database work out of the native SDK callback thread.

`bStatus` is interpreted according to the vendor's SDK structure comment: true means a successful card scan (`granted`), false means a failed scan (`denied`). The raw `bStatus`, `emStatus`, and `nErrorCode` values are also retained. Device-local event time and SDK-marked real UTC time are stored separately.

### Access-event endpoints

- `GET /access-events?limit=100&offset=0`
- `GET /access-events?device_id=1&limit=100`
- `GET /access-events?card_number=FB66983B`
- `GET /access-events/summary` (optional `device_id` filter)
- `GET /access-events/{event_id}`

The list endpoint returns newest-first events and is intended for dashboard/history integration. This repository package is the FastAPI backend; it does not include a separate web frontend.

### Network interfaces

- `GET /api/network/interfaces` lists active Ethernet/LAN IPv4 adapters with MAC information.
- `GET /device-initialization/interfaces` returns the Ethernet IPv4 addresses that LAN discovery uses by default. An explicit `local_ip` supplied to the discovery endpoint is still honored.

The adapter filter is based on interface names containing `Ethernet`, `eth`, or `LAN`. Rename a Windows adapter to an Ethernet/LAN-style name if it is not detected by this filter.
