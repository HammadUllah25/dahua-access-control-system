# Dahua Access Control API Starter

FastAPI backend for Dahua ASI1201E access controllers using the Dahua NetSDK Python wheel.

## Current modules

**Version 1.1.5 API surface:** the legacy People and IC Cards router (`/persons/*` and old `/devices/{device_id}/cards/*`) and standalone Network router (`/api/network/interfaces`) are disabled and return 404. The required `/device-initialization/interfaces` endpoint remains available. Historical sections below may mention retired endpoints; do not treat those examples as active API routes.


- Device registration, connection/disconnection and TCP health monitoring.
- **Station-user RFID workflow:** each named station user has one active RFID card and one predefined or custom operational role (`MANAGER`, `ADMIN`, `STAFF`, `CUSTOMER`, or a station-defined role).
- Billability is a separate user-level setting that defaults from the selected role; only qualifying successful ENTRY events for billable users can create usage charges.
- Effective-dated per-station rates, expected-collection calculations, cash collection records and outstanding balances.
- Station, date-range, trend and card-wise reporting APIs, plus the built-in read-only dashboard at `/dashboard-ui`.
- Cloud-owned card assignments, controller inventory checks and administrator-confirmed reprovisioning after a verified factory reset.
- Legacy person-based API modules and data models are retained for database compatibility, but their HTTP router is not mounted in version 1.1.5. New station registrations use the station-user and user-bound card-enrollment APIs documented below.

## Windows installation (provided SDK wheel)

1. Extract this `dahua_access_starter` folder to your backend directory.
2. Keep your existing `data/dahua_access.db`, `data/device_secret.key`, and any local `.env` file. Do not replace them with files from another machine.
3. Double-click `install.bat`. It creates the project-local `.venv`, installs `requirements.txt`, installs the bundled Dahua NetSDK wheel from `vendor/`, and runs a setup check.
4. Double-click `run.bat` to start the API.
5. Open `http://127.0.0.1:8000/dashboard-ui` for the read-only station dashboard or `http://127.0.0.1:8000/docs` for setup and management APIs.

The project-local `.venv` is intentional: the NetSDK wheel must be installed into the same interpreter that starts Uvicorn. Do not rely on a separate `backend/venv` or a globally installed Python package.



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
.\.venv\Scripts\python.exe tools\verify_initialization_sdk.py
```

This check validates the ctypes structures and enums without loading the native DLL or changing a controller. The mocked orchestration test can be run with `.\.venv\Scripts\python.exe tools\test_initialization_mock.py` after `install.bat`. The native discovery/initialization calls still need to be run on the Windows PC with the ASI1201E on the same LAN. The release bundle includes the Dahua NetSDK Windows x64 wheel and installs it in the project-local `.venv`.

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

The SDK's `NET_RECORDSET_ACCESS_CTL_CARD` declaration marks `szUserID` as unsupported on this legacy record format. Therefore `Person` is the central application record, while `szCardName`, card UID, validity, door indexes and time-section indexes are synchronized to the controller. The application keeps the `person_id` ↔ device-card assignment mapping. Creating/updating a `/persons` record changes the central database only; both direct assignment and scan-to-enroll confirmation use the same physical card-record insertion path. If a person's name changes, update the card's `card_name` separately when you want the controller display name changed.

## Important permission/index note

For initial ASI1201E testing, the card schema defaults to Door index `0` and time-section index `0` (typically Door 1 / the first device time section). Confirm these indexes against the controller's actual Door Parameters and time-template configuration before production use. The card can be registered successfully while still being denied access if the selected door/time schedule is not valid.

The SDK card structure stores validity as `NET_TIME` and its comments state that this record does not support hour/minute/second precision. The API therefore accepts dates only. Exact access windows belong in the device time-section configuration, which is a later module.

## Verify the IC-card SDK structures

Run this after `install.bat` has installed the wheel into the project-local `.venv`:

```powershell
.\.venv\Scripts\python.exe tools\verify_card_sdk.py
```

The verifier checks the exact enum values, ctypes field names and structure sizes used by this module. It does not initialize the native DLL or modify the physical controller.

## Install / run on Windows

Run `install.bat` once to create `.venv` and install the requirements plus the bundled Dahua SDK wheel. Then run `run.bat`. Both scripts explicitly use `.venv\Scripts\python.exe`; a separate parent `backend\venv` is not used.

Open `http://127.0.0.1:8000/docs`.

Keep your existing `data` folder, `device_secret.key`, and SQLite database when replacing the source. The installer creates a fresh project-local `.venv`. Existing device/person/card data is preserved; startup migrations are additive.

## Legacy API workflow: person-based card assignment

This older workflow is retained for existing projects and is not required for the station-first USER/STAFF model described later in this README.

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

The native update path initializes `NET_OUT_FIND_RECORD_PARAM.dwSize` before calling `FindRecord`. When the card UID is unchanged, it skips the separate duplicate-UID lookup and performs only the record reload needed for the update. A successful SDK return means the controller accepted the write; verify the card record and test with a spare card before relying on a validity change for access revocation.

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

The separate personnel-profile lookup (`GET /devices/{device_id}/person-records/{device_user_id}`) is optional and firmware-dependent. For ASI1201E-family devices it returns HTTP 501 by design and is not part of the card-record workflow; use `GET /persons` and `GET /devices/{device_id}/cards` to view the central person and its application card assignments. The native card-record list also skips the personnel service on these devices.

The card-record response includes the fields available from the native card record: card status/type/UID, validity dates, creation timestamp when populated, door and time-section indexes, and additional non-secret card metadata. Personnel profile fields are separate and may not be supported by every controller/firmware.

**Credential and biometric handling:** the API never returns `szPsw`, the card password itself, or raw face-template bytes. It returns only `password_configured` and a face-template count. Face photographs/templates use a separate Dahua face service; the example SmartPSS Lite screenshot shows placeholder silhouettes rather than uploaded images.

**Date limitation:** the `NET_RECORDSET_ACCESS_CTL_CARD` structure in the supplied NetSDK exposes `stuCreateTime` (card-record creation time) but no card-record modification timestamp. The person service exposes `stuUpdateTime` for the person profile, which is returned separately as `person_profile.update_time`; it must not be presented as the card's change date.

The optional personnel lookup uses `OperateAccessUserService`; it is not called by the ASI1201E card-enrollment confirmation flow. The observed ASI1201E installation returned SDK error `0x00000015` for this lookup, so the feature should be treated as unverified/firmware-dependent until tested independently.

---


## Scan-to-enroll a new IC card

The scan-to-enroll workflow listens to the selected controller's Dahua access-control alarm stream. It captures the first event containing a card UID during the active enrollment window. An unregistered card must cause the controller to emit an access-control event containing `szCardNo`; some firmware/configurations may not report unknown-card scans. If no UID is reported, the session remains `waiting` and eventually expires.

### Workflow

1. Create the central person using `POST /persons`.
2. Start a timed scan window using `POST /devices/{device_id}/card-enrollments`.
3. Present the physical IC card to the ASI1201E reader.
4. Poll `GET /devices/{device_id}/card-enrollments/{session_token}` until `status` becomes `captured`.
5. Confirm using `POST /devices/{device_id}/card-enrollments/{session_token}/confirm`.
6. The backend writes the captured UID as a Dahua IC-card record through the same legacy record-set insert path used by direct card assignment, then saves the application person/card assignment in SQLite.

Start request:

```json
{
  "timeout_seconds": 90
}
```

Confirm request (the card number is intentionally taken from the captured event; do not supply it again):

```json
{
  "person_id": 1,
  "card_name": "Hammad RFID Card",
  "card_type": "general",
  "is_valid": true,
  "valid_from": "2026-11-12",
  "valid_until": "2037-12-31",
  "door_indices": [0],
  "time_section_indices": [0]
}
```

The confirmation endpoint does not create a separate Dahua personnel profile. It writes the card record using the existing `CLIENT_ControlDevice` / `RECORDSET_INSERT` implementation and stores the relationship to `person_id` in the central application database. This avoids making enrollment depend on the optional `OperateAccessUserService` personnel lookup that failed with SDK error `0x00000015` on the reported ASI1201E installation. The device-side `szUserID` field is not relied upon for this model/workflow.

Additional endpoints:

- `GET /devices/{device_id}/card-enrollments/{session_token}` — poll enrollment status and captured UID.
- `DELETE /devices/{device_id}/card-enrollments/{session_token}` — cancel an unfinished enrollment.

Only one active enrollment is allowed per device at a time. Enrollment sessions are held in backend memory and are cleared when the API process restarts. A failed confirmation leaves the captured UID available for retry. The normal card-assignment helper attempts a compensating controller-card delete if the hardware insert succeeds but the local database commit fails; verify controller records if that cleanup reports an error.

**Hardware verification required:** the SDK structures and insert/remove operations are checked against the supplied NetSDK 3.060 Python wheel, but this environment cannot verify that the ASI1201E firmware reports an unknown card UID or accepts the native card INSERT operation. Test with one spare card and one test person first. Confirm `status=captured`, then run `POST /devices/{device_id}/inventory-check` and confirm the inventory reports `in_sync`. Finally test the physical door and its configured schedule before using real access credentials.

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

### Interface discovery

- `GET /device-initialization/interfaces` returns the Ethernet IPv4 addresses that LAN discovery uses by default. An explicit `local_ip` supplied to the discovery endpoint is still honored.

The standalone `GET /api/network/interfaces` route is disabled in version 1.1.5. The device-initialization interface endpoint is the supported operation for the setup wizard.

## Live device status for the Next.js dashboard

The backend runs a background monitor independently of dashboard users. By default it checks each registered controller every 10 seconds, tests its configured TCP port, and verifies that the backend still owns a Dahua SDK login session. A device is marked offline after two consecutive failed TCP checks or an SDK login failure. The monitor stores the status and health timestamps in the database.

### Initial status snapshot

`GET /devices/status` returns a compact, credential-free list and summary counts:

```json
{
  "items": [
    {
      "device_id": 1,
      "name": "Washroom Controller",
      "host": "192.168.0.2",
      "port": 37777,
      "model": "ASI1201E",
      "serial_number": "AM029C2PAJ1057A",
      "status": "online",
      "monitoring_enabled": true,
      "last_seen": "2026-11-12T06:40:00+00:00",
      "last_health_check_at": "2026-11-12T06:40:00+00:00",
      "consecutive_failures": 0,
      "last_error": null
    }
  ],
  "summary": {"total": 1, "online": 1, "offline": 0, "pending": 0, "unknown": 0}
}
```

### WebSocket live updates

Connect to `ws://localhost:8000/ws/devices` (use `wss://` in production). Optionally subscribe to one device with `?device_id=1`. The connection first sends `device.status.snapshot`, then pushes events whenever a status changes. It also sends a heartbeat every 25 seconds when there are no updates.

Event types:

- `device.status.snapshot` — initial device list and summary counts.
- `device.status.changed` — one device's latest state after an online/offline transition or manual connection-state change.
- `device.deleted` — a registered device was deleted.
- `heartbeat` — connection liveness message.
- `pong` — response to an optional client message `{"type":"ping"}`.

Example status-change event:

```json
{
  "type": "device.status.changed",
  "data": {
    "device_id": 1,
    "status": "offline",
    "last_seen": "2026-11-12T06:40:00+00:00",
    "consecutive_failures": 2,
    "last_error": "Health check failed: TCP 192.168.0.2:37777 is unreachable.",
    "reason": "monitor_unreachable"
  }
}
```

The actual status payload includes device identity, name, host/port, monitoring state, timestamps, failure count, and error details; it never includes the device username or password. See `docs/NEXTJS_DEVICE_STATUS_INTEGRATION.md` for a client-side Next.js example.

### Monitoring semantics and deployment notes

`online` means the configured TCP port is reachable and this backend process holds a NetSDK login session. This is an application health check, not a controller-originated heartbeat. Status detection can take roughly two monitor intervals after a sudden network loss (default: around 20 seconds), plus the TCP timeout. The monitor is single-process and must run with one Uvicorn worker because SDK login handles are process-local. Do not run multiple API replicas with independent monitors against the same devices. The current API has no authentication layer; keep it on a trusted LAN/VPN until authentication and authorization are added before public exposure.

---

# Legacy direct station-card workflow (USER / STAFF)

This section documents the earlier direct station-card workflow for backward compatibility. New registrations should use the station-user flow in the section **Station users, operational roles, and RFID card assignment** below. The older person-based REST routes are disabled in version 1.1.5; this section is retained as historical documentation for the earlier direct station-card model.

## Important data ownership rule

The application database is the system of record. Dahua controller records are only the local working copy needed to make access decisions at the door. A controller reset must not delete stations, cards, roles, rates, access-event history or cash-collection records from the application database.

For a central deployment, configure PostgreSQL using `DATABASE_URL` and set a persistent `DEVICE_ENCRYPTION_KEY` generated once with Fernet. The same key must be supplied securely to every API process/worker that needs to decrypt device passwords. Do not rotate or regenerate this key casually; encrypted device credentials cannot be decrypted with a different key. Keep `.env`, the real local `data/device_secret.key`, and the SQLite database out of source archives and source control.

## Station-first setup workflow

1. Register a controller using the existing `POST /devices` route.
2. Create a station using `POST /stations`:

```json
{
  "station_code": "ST-001",
  "name": "Station 001",
  "city": "Karachi"
}
```

3. Associate the controller with the station using `POST /stations/{station_id}/devices/{device_id}`.
4. Add a billable customer card using `POST /stations/{station_id}/cards`:

```json
{
  "device_id": 1,
  "card_number": "FB66983B",
  "role": "USER",
  "card_name": "Customer washroom card",
  "is_valid": true,
  "valid_from": "2026-11-13",
  "valid_until": "2037-12-31",
  "door_indices": [0],
  "time_section_indices": [0]
}
```

5. Add the staff card the same way with `"role": "STAFF"`. `USER` defaults to billable and `STAFF` defaults to non-billable. The event processor charges only successful `ENTRY` events for active, valid, billable `USER` assignments.
6. Configure the USER per-entry rate using `POST /stations/{station_id}/rates`:

```json
{
  "role": "USER",
  "rate_per_use": "20.00",
  "currency": "PKR",
  "effective_from": "2026-11-13"
}
```

The amount above is an example only. Rate periods for the same station and role cannot overlap. Each qualifying event snapshots the effective rate so later rate changes do not rewrite historical charges.
7. Record actual cash received using `POST /stations/{station_id}/cash-collections`:

```json
{
  "period_start": "2026-11-13",
  "period_end": "2026-11-13",
  "amount": "2500.00",
  "currency": "PKR",
  "received_by": "Station cashier",
  "reference": "RECEIPT-001"
}
```

### Convert an existing person-based card without deleting it

If a physical card was already enrolled through the older `/persons` workflow, do **not** post it again to `/stations/{station_id}/cards`; that endpoint correctly rejects a duplicate card number. Use `POST /stations/{station_id}/cards/adopt-existing` instead. This creates the station role assignment from the existing cloud `AccessCard` row, keeps the original Person and AccessCard records intact, and does not make a hardware call.

Example for an existing customer card:

```json
{
  "device_id": 1,
  "card_number": "FB66983B",
  "role": "USER",
  "card_name": "Customer Card 01",
  "is_billable": true
}
```

For a real staff RFID card, use its actual UID with `"role": "STAFF"` and `"is_billable": false`. Adopt only cards that physically exist; do not convert placeholder/test card numbers just because they appear in the old database. Adoption intentionally sets `device_record_no` to null and the station assignment to `needs_reprovisioning`, because native record numbers from before a factory reset cannot be trusted.

After adopting the required cards, restore them to a controller that has been physically confirmed factory-reset using `POST /devices/{device_id}/reprovision`:

```json
{
  "confirmation": "REPROVISION_FROM_CLOUD",
  "controller_confirmed_factory_reset": true
}
```

This confirmation bypasses the SDK inventory preflight; use it only when the controller is known to be empty. The endpoint inserts the station assignments and attempts a readback. On ASI1201E firmware where `FindRecord` is unsupported, the response may be `verification_required`; in that case check the restored cards in SmartPSS and physically scan each card before treating the controller as recovered. The backend will not label those records `synced` solely because an insert call returned success.

Do not repeat the confirmed restore request after it has started. The API blocks a second confirmed attempt to avoid duplicate hardware inserts when the controller's inventory API cannot be queried. If the restore returns `verification_required`, and you have checked **every** expected card in SmartPSS and tested access with each physical card, call `POST /devices/{device_id}/reprovision/manual-verification`:

```json
{
  "confirmation": "I_VERIFIED_EACH_CARD_IN_SMARTPSS_AND_TESTED_ACCESS",
  "verified_card_numbers": ["FB66983B"]
}
```

The list must exactly match the station-card assignments for that controller. This records that the administrator completed manual verification; it does not claim that the unsupported SDK inventory readback API works.

## Dashboard and reporting

- `GET /dashboard-ui` — local read-only dashboard page.
- `GET /dashboard/summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — scan, role, expected collection, cash and outstanding summary.
- `GET /dashboard/stations` — station-by-station device/card/usage overview.
- `GET /reports/usage?group_by=day|week|month|year` — grouped usage report.
- `GET /reports/card-usage` — per-card scan and billable-entry summary.
- `GET /access-events?station_id=1&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — detailed event list.
- `GET /stations/{station_id}/cash-collections` — cash collection history.

The dashboard is a lightweight built-in HTML view served by FastAPI; the uploaded project did not contain a separate React/Next.js frontend. Station/card creation, rate changes and cash entry are currently handled through the APIs in `/docs`.

## Factory-reset and recovery workflow

1. A controller reset does not remove anything from the cloud/application database. If the reset also restores factory credentials or network settings, first reinitialize the controller and update its saved host/username/password in the application. The backend cannot restore cards until the controller is reachable and a valid authenticated SDK session is established.
2. Run `POST /devices/{device_id}/inventory-check` after reconnecting. A successful inventory comparison may report missing cloud cards and create a pending reprovision job.
3. If the controller was physically factory-reset and the SDK inventory API cannot read its card records, an administrator may explicitly confirm that fact by calling `POST /devices/{device_id}/reprovision` with:

```json
{
  "confirmation": "REPROVISION_FROM_CLOUD",
  "controller_confirmed_factory_reset": true
}
```

4. The backend writes the cloud card assignments back to the controller and attempts a readback verification. It does not delete unexpected controller cards automatically.
5. If the SDK readback is unsupported or fails, the device is marked `verification_required`/`unknown` and card assignments are not falsely reported as fully synchronized. Verify the result using a supported Dahua management tool or firmware-specific method before declaring recovery complete.

**Never run the confirmed-factory-reset reprovision action unless an administrator has physically verified that this controller was reset and is intended to be restored from the cloud inventory.**

## Reporting and accounting rules

- Default billable unit: one successful `ENTRY` event on an active, valid `USER` card.
- `STAFF` card events are recorded but non-billable by default.
- Denied scans and non-entry events are not charged.
- The applied rate is captured on the event at the time it is persisted.
- The rule currently treats every separate successful USER `ENTRY` callback as a billable use. A visit/session cooldown or duplicate-tap suppression policy has not been added; decide that business rule and test actual ASI1201E callback behavior before invoicing automatically.
- In the observed ASI1201E event messages, the native `event_id` was `0` and `sequence` was `null`. The backend deduplicates only when a stable native event identifier exists; where it does not, it cannot promise exactly-once event accounting. Validate the device callback delivery pattern and add a durable event-id/outbox strategy before using reports as the sole financial ledger.
- Expected collection is calculated from those billable event snapshots.
- Cash collection records separately store the usage period being settled and the date cash was physically received. The summary distinguishes `actual_cash_collected` (allocated to the selected usage period) from `cash_received_during_report_period` (received inside the selected dates).
- Existing access events recorded before station/card-role assignments have no role/rate snapshot and are not retroactively billed. Existing person-based cards are not automatically converted because their USER/STAFF role cannot be safely inferred; create/review their station assignments explicitly.

## Deployment and hardware limitations — read before production

- The supplied NetSDK wheel and native SDK are Windows x64. Device SDK calls must currently run on a supported Windows host where the controllers are reachable over the network. A single cloud VPS generally cannot directly reach controllers behind 100 separate station LANs unless you provide a VPN/site-to-site network or a secure outbound Windows site-agent architecture.
- This release provides station-aware data structures, APIs, reports, explicit inventory checks and an administrator-confirmed reprovision path. It does **not** yet implement autonomous factory-reset detection. A reset is discovered by inventory comparison or an administrator report; automatic physical reset detection is model/firmware dependent.
- The access-event persistence queue is in-process. It is suitable for development/single-process testing, not a guarantee of zero event loss across process restarts or network outages. Production deployment needs a durable edge outbox/message queue and retry/acknowledgement flow.
- No application user authentication/role authorization has been added in this release. Keep the API and `/dashboard-ui` on a private LAN/VPN; do not expose it to the public internet. Add authenticated administrators, least-privilege station operators, TLS, audit trails and secret-manager integration before a live 100-station rollout.
- The ASI1201E has previously returned `FindRecord failed: The device does not support current operation` in this installation. The code deliberately treats that as unknown inventory, not an empty device. Physical card insert/freeze/reprovision/readback must be tested on the actual controller and firmware before relying on it operationally.
- Do not run multiple Uvicorn workers that each initialize their own NetSDK sessions against the same devices. Use a dedicated device worker/agent architecture for a distributed rollout.

## Upgrade safety

Back up your existing `data/dahua_access.db` and `data/device_secret.key` before replacing source files. This package excludes local runtime databases and encryption keys. Keep your existing files in place; do not overwrite them with the package's empty `data` folder. The added startup migration is additive and is intended to preserve the existing person/card data. Test the upgrade against a backup first.

---

## Station users, operational roles, and RFID card assignment

This update introduces the station operational-user workflow. It is separate from software/dashboard accounts: a `StationUser` is a named person or label at a physical station and does not log in to the application.

### Operational roles

The application seeds four predefined, global operational roles at startup:

| Code | Display name | Default billable |
|---|---|---:|
| `MANAGER` | Manager | No |
| `ADMIN` | Admin | No |
| `STAFF` | Staff | No |
| `CUSTOMER` | Customer | Yes |

A station can also create custom operational roles. Built-in roles cannot be edited or deactivated. Custom roles are station-scoped and can be deactivated without deleting historical users/events. `is_billable` can be overridden per station user; when the override is `null`, the role's `default_is_billable` is used.

These are RFID/operational classifications, not dashboard permission roles. Role-specific Dahua access profiles are not automated in this phase: the physical card still receives explicit door and time-section indexes during enrollment.

### Recommended setup sequence in Swagger

1. Check the local network interfaces: `GET /device-initialization/interfaces`.
2. If the controller is factory-new and uninitialized, discover it with `POST /device-initialization/discover`, then initialize it with `POST /device-initialization/initialize`. Do not initialize an already initialized controller.
3. Register the controller with `POST /devices`. Set `connect_now: true` to attempt connection immediately. For an already registered controller, use `POST /devices/{device_id}/connect`.
4. Assign the registered controller to its station with `POST /stations/{station_id}/devices/{device_id}`.
5. Load available roles using `GET /stations/{station_id}/roles`.
6. Create a named station user using `POST /stations/{station_id}/users` and a role ID returned by the roles endpoint.
7. Start a card scan using `POST /stations/{station_id}/users/{user_id}/card-enrollments` with `device_id` and optional `timeout_seconds`.
8. Present the RFID card to the Dahua reader. Poll `GET /stations/{station_id}/users/{user_id}/card-enrollments/{session_token}` until its status is `captured`.
9. Confirm the captured card using `POST /stations/{station_id}/users/{user_id}/card-enrollments/{session_token}/confirm`. The UID comes from the scan event; it is not supplied by the caller.
10. Review the result at `GET /stations/{station_id}/users/{user_id}` or `GET /stations/{station_id}/cards`.

### New endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/stations/{station_id}/roles` | List predefined and station custom roles |
| POST | `/stations/{station_id}/roles` | Create a custom operational role |
| PATCH | `/stations/{station_id}/roles/{role_id}` | Update a station custom role |
| DELETE | `/stations/{station_id}/roles/{role_id}` | Deactivate a station custom role |
| POST | `/stations/{station_id}/users` | Create a named station user with a role |
| GET | `/stations/{station_id}/users` | List station users and their active cards |
| GET | `/stations/{station_id}/users/{user_id}` | Get one station user and active card |
| PATCH | `/stations/{station_id}/users/{user_id}` | Update name, phone, role, billing override, or active status |
| POST | `/stations/{station_id}/users/{user_id}/cards/adopt` | Link an existing station-card record without re-enrolling it |
| POST | `/stations/{station_id}/users/{user_id}/card-enrollments` | Start a Dahua RFID scan for a specific user |
| GET | `/stations/{station_id}/users/{user_id}/card-enrollments/{session_token}` | Read the user-bound scan session |
| POST | `/stations/{station_id}/users/{user_id}/card-enrollments/{session_token}/confirm` | Register the captured card and assign it to the user |
| GET | `/stations/{station_id}/users/{user_id}/card-history` | List current and historical card assignments |
| DELETE | `/stations/{station_id}/users/{user_id}/card` | Revoke/deactivate the active card on the controller and close the assignment |

A station user may have only one active card assignment. A physical station-card record may have only one active user assignment. The `user_card_assignments` table preserves previous assignments when cards are replaced or reassigned. The station's existing `/cards` endpoint now includes the linked user's name and operational role when a current user-card link exists.

### Example requests

List roles:

```json
GET /stations/1/roles
```

Create a custom role:

```json
{
  "name": "Cleaning Team",
  "description": "Washroom cleaning personnel",
  "default_is_billable": false
}
```

Create a station user (use a real `role_id` from the roles response):

```json
{
  "name": "Ahmed",
  "phone": "03001234567",
  "role_id": 4,
  "is_billable": null
}
```

Start card enrollment:

```json
{
  "device_id": 1,
  "timeout_seconds": 90
}
```

Confirm the captured scan:

```json
{
  "card_name": "Ahmed",
  "card_type": "general",
  "is_valid": true,
  "valid_from": "2026-11-14",
  "valid_until": "2037-12-31",
  "door_indices": [0],
  "time_section_indices": [0]
}
```

### Data model and compatibility

- `operational_roles`: predefined global roles and station custom roles.
- `station_users`: station name/label, selected operational role, contact, and optional billable override.
- `user_card_assignments`: historical user-to-station-card links, with a partial unique index enforcing one active card per user and one active user per card record.
- Existing `station_card_assignments` remains the controller-card inventory record for backward compatibility.
- The older `/persons` and `/devices/{device_id}/card-enrollments` REST workflow is disabled in version 1.1.5. New station registrations must use the `/stations/{station_id}/users` endpoints above.
- Existing station-card records can be linked to a newly created station user with the `/cards/adopt` endpoint. This does not change the controller. It marks that assignment and the device inventory as requiring verification; it does not assume that an old `synced` flag proves the controller still contains the card.
- New card registration is marked `pending_verification` after insertion. Do not treat a successful SDK insert call by itself as a verified readback.

### Access-event and billing behavior

Incoming events resolve the active card assignment to the station user and current operational role. The event stores a snapshot of the user ID, user name and role code. A charge is considered only for a qualifying `granted` `ENTRY` event when the station/card/user are active and the effective user billing flag is true. Denied scans remain in event history and are not billable.

For compatibility, the current rate table still uses the existing `USER` and `STAFF` pricing buckets: billable operational roles use the `USER` rate bucket; non-billable roles do not create usage charges. Role-specific price schedules are a separate future enhancement.

### Database upgrade and backup

On application startup, new tables are created and the two station-user snapshot columns are added to the existing `access_events` table if missing. The four predefined operational roles are seeded idempotently. Existing station/device/card/event records are not deleted or replaced.

Before applying an update to an existing installation, stop the API and back up:

- `data/dahua_access.db`
- `data/device_secret.key`

Do not replace the `.env`, `.venv`, live database, or encryption key when copying updated source files. The database and its encryption key must be kept together.

### Verification performed for this update

Run the offline smoke test from the project root with `pip install -r requirements-test.txt` followed by `python tests/smoke_station_user_workflow.py`. It uses a temporary SQLite database and mocked Dahua insert/update calls; it does not connect to the physical controller or touch the installation database.

The development verification suite exercised role seeding/listing, custom role create/update protections, station-user creation, user-bound card enrollment, confirmation with a mocked Dahua card-insert operation, one-active-card enforcement, card/user read APIs, and access-event resolution to a custom role. A copy of the SQLite database bundled in the supplied project archive was upgraded; Station 1, Device 1, card `FB66983B`, and 27 historical access events were preserved. The Dahua hardware itself was not connected or exercised by these offline tests. Perform one controlled physical card enrollment and access test before using the new workflow operationally.


## Controller-only card record deletion (advanced)

Use this endpoint only when a physical Dahua card record remains on the controller but its application assignment has already been removed:

`DELETE /devices/{device_id}/cards/device-records/{record_number}`

Request body example for the verified device record `16872` / card UID `000041E8`:

```json
{
  "card_number": "000041E8",
  "confirmation": "DELETE_CONTROLLER_CARD:16872:000041E8"
}
```

The endpoint connects to the controller, reads the card list, verifies the exact record number and card UID, and then removes that controller card record. It refuses deletion if a matching cloud-side station or legacy card assignment still exists. It does not delete application assignments or access-event history. After success, device inventory is set to `unknown`; run a fresh inventory check before enrolling cards. This operation is irreversible on the controller and should be used only after confirming the record identity.

## Next.js frontend API handoff

The current frontend integration scope, endpoint groups, device initialization sequence, WebSocket status messages, station-user/RFID workflow, and legacy APIs to avoid are documented in `docs/NEXTJS_FRONTEND_API_HANDOFF.md`. This guide reflects the current 1.1.5 mounted backend routes.



## Station-user card reactivation

To reactivate an existing card assignment for its previous station user, use `POST /stations/{station_id}/users/{user_id}/cards/{assignment_id}/activate`. This preserves the old inactive history row and creates a new active link. Run controller inventory verification afterwards. The endpoint does not extend an expired card's validity or alter its door/time-section permissions. See `docs/NEXTJS_FRONTEND_API_HANDOFF.md`.


## API surface note (v1.1.5)

The legacy People and IC Cards router and standalone Network router are intentionally not mounted. The supported device initialization interface API remains `/device-initialization/interfaces`. Legacy model and migration code is retained for compatibility with existing databases.
