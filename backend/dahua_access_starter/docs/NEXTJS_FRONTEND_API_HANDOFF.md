# Next.js Frontend API Integration Guide

**Project:** Dahua RFID Washroom Access Management System  
**Backend:** FastAPI + SQLAlchemy + Dahua NetSDK  
**API version:** 1.1.5  
**Local base URL:** `http://127.0.0.1:8000`  
**Swagger:** `http://127.0.0.1:8000/docs`

This document describes the routes implemented in this backend package. Swagger at the running backend is the final source for request and response schemas. The complete mounted REST API specification is included at `docs/openapi-frontend-v1.1.5.json`. The legacy People and IC Cards router and standalone Network router are not mounted in this release, so those endpoints are unavailable and do not appear in Swagger. The required device-initialization interface route remains available at `/device-initialization/interfaces`. The device WebSocket is documented below because WebSockets are not part of the REST OpenAPI document.

---

## 1. Architecture and responsibilities

- **Next.js:** dashboard screens, forms, tables, filters, confirmations, loading/error states, and WebSocket client.
- **FastAPI backend:** business rules, database operations, card/user assignment, billing calculations, access-event storage, device monitoring, and API authorization when added.
- **Dahua NetSDK:** all communication with the physical controller. It is used only by the backend; the browser must never connect directly to the controller or SDK.

A station operational user (for example Ahmed, CUSTOMER, STAFF or MANAGER) is not a dashboard login account. Dashboard login/RBAC is a separate module and is not implemented by these station-user APIs.

## 2. Main frontend modules

1. Stations
2. Device initialization
3. Device registration and connection
4. Device online/offline monitoring
5. Station-device assignment
6. Operational roles
7. Station users
8. RFID enrollment and card management
9. Controller inventory verification
10. Access events
11. Rates, cash collections, and reports

## 3. Station management APIs

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/stations` | Create a station |
| `GET` | `/stations` | List stations; optional `active_only=true` |
| `GET` | `/stations/{station_id}` | Station details |
| `PUT` | `/stations/{station_id}` | Update station details |
| `GET` | `/stations/{station_id}/devices` | List devices assigned to a station |
| `POST` | `/stations/{station_id}/devices/{device_id}` | Assign a device to a station |
| `DELETE` | `/stations/{station_id}/devices/{device_id}` | Remove the station-device association |

## 4. Device initialization and registration

The setup wizard is for adding a controller to the software. Initialization is only required when the physical controller itself has not yet been initialized.

### 4.1 Initialization wizard APIs

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/device-initialization/interfaces` | List local IPv4 interfaces available to the backend for device discovery |
| `POST` | `/device-initialization/discover` | Discover Dahua devices on the selected local network |
| `POST` | `/device-initialization/initialize` | Create the first administrator account on an uninitialized controller |

For a controller that is already initialized, do not initialize it again. Use its existing network and login details in the device-registration step.

### 4.2 Device registration and connection APIs

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/devices` | Register a controller in the backend; request can set `connect_now` and `monitoring_enabled` |
| `GET` | `/devices` | List registered controllers |
| `GET` | `/devices/{device_id}` | Controller details |
| `PUT` | `/devices/{device_id}` | Update controller connection details or monitoring setting |
| `POST` | `/devices/{device_id}/connect` | Connect/reconnect using NetSDK and enable monitoring |
| `POST` | `/devices/{device_id}/disconnect` | Disconnect and disable monitoring for that controller |
| `DELETE` | `/devices/{device_id}` | Delete a controller; backend blocks deletion while station card assignments remain |

Example `POST /devices` request:

```json
{
  "name": "Petrol Pump Washroom Controller",
  "connection_type": "ip_domain",
  "host": "192.168.0.2",
  "port": 37777,
  "username": "admin",
  "password": "DEVICE_PASSWORD",
  "model": "ASI1201E",
  "serial_number": "AM029C2PAJ1057A",
  "mac_address": "30:DD:AA:3D:A2:11",
  "connect_now": true,
  "monitoring_enabled": true
}
```

After registration, assign the device to the selected station using `POST /stations/{station_id}/devices/{device_id}`. A device can be registered before it is attached to a station.

**Important:** `POST /devices/{device_id}/disconnect` is an administrative action. It also sets `monitoring_enabled=false`, so the normal dashboard should not call it merely to refresh or test a connection.

## 5. Device online/offline monitoring and WebSocket

### 5.1 Initial status and monitoring APIs

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/devices/status` | Credential-free status snapshot for dashboard load; returns `items` and `summary` |
| `POST` | `/devices/{device_id}/health-check` | Run one immediate health check |
| `GET` | `/devices/monitor/status` | Read background monitor service status/configuration |

### 5.2 WebSocket

Connect to:

```text
ws://127.0.0.1:8000/ws/devices
```

Optional single-device filter:

```text
ws://127.0.0.1:8000/ws/devices?device_id=1
```

Production must use `wss://` with the deployed backend domain.

The backend sends these messages:

| Message type | Meaning |
|---|---|
| `device.status.snapshot` | Initial full snapshot after the socket connects; contains `data.devices`, `data.summary`, and `data.generated_at` |
| `device.status.changed` | One device's status/health fields changed; device data is in `data` |
| `device.deleted` | A device was deleted; remove its `device_id` from frontend state |
| `heartbeat` | Server-side connection-liveness message |
| `pong` | Response to a client `{"type":"ping"}` |

Example status-change message:

```json
{
  "type": "device.status.changed",
  "data": {
    "device_id": 1,
    "name": "Petrol Pump Washroom Controller",
    "status": "offline",
    "monitoring_enabled": true,
    "reason": "monitor_unreachable"
  }
}
```

Frontend implementation:

1. Call `GET /devices/status` when the page loads.
2. Open the WebSocket and use `device.status.snapshot` as the authoritative socket snapshot.
3. Update only the affected device when `device.status.changed` arrives.
4. Remove the device when `device.deleted` arrives.
5. Show socket connection state and reconnect with backoff after a disconnect.
6. Optionally send `{"type":"ping"}`; handle `pong`. `heartbeat` does not require a UI change.

**Online-status definition:** the backend monitor checks TCP reachability and requires this backend process to hold a NetSDK login session. This is not a device-originated heartbeat. The monitor runs in the backend process; the project currently expects a single API process to own the SDK sessions and monitor.

## 6. Operational roles and station users

### 6.1 Operational roles

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/stations/{station_id}/roles` | List active predefined and custom roles; use `include_inactive=true` to include inactive custom roles |
| `POST` | `/stations/{station_id}/roles` | Create a station-specific custom role |
| `PATCH` | `/stations/{station_id}/roles/{role_id}` | Update a custom role; predefined roles cannot be changed |
| `DELETE` | `/stations/{station_id}/roles/{role_id}` | Deactivate a custom role; predefined roles cannot be deactivated |

Predefined roles are `MANAGER`, `ADMIN`, `STAFF`, and `CUSTOMER`. Their default billability is maintained by the backend. Always use role IDs returned by the roles API; do not hardcode IDs.

### 6.2 Station users

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/stations/{station_id}/users` | Create a station operational user |
| `GET` | `/stations/{station_id}/users` | List users; optional `active_only=true` and `role_id` filters |
| `GET` | `/stations/{station_id}/users/{user_id}` | User details and current active card |
| `PATCH` | `/stations/{station_id}/users/{user_id}` | Update user, role, billability override, or active state |

Example create-user request:

```json
{
  "name": "Ahmed",
  "phone": "03001234567",
  "role_id": 4,
  "is_billable": null
}
```

`is_billable: null` means inherit the role's default. A true/false value overrides that default for the user. A user must have their card deactivated before the backend allows the user record itself to be deactivated.

## 7. RFID enrollment and card management

### 7.1 Normal new-card enrollment

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/stations/{station_id}/users/{user_id}/card-enrollments` | Start a card-scan session; requires `device_id` and optionally `timeout_seconds` |
| `GET` | `/stations/{station_id}/users/{user_id}/card-enrollments/{session_token}` | Poll session status and captured card number |
| `POST` | `/stations/{station_id}/users/{user_id}/card-enrollments/{session_token}/confirm` | Write captured card to controller and create the station-user assignment |
| `GET` | `/stations/{station_id}/users/{user_id}/card-history` | Read historical card assignments for the user |
| `GET` | `/stations/{station_id}/cards` | List station card assignments with linked user/role fields; optional `active_only=true` and `role` filters |
| `DELETE` | `/stations/{station_id}/users/{user_id}/card` | Freeze/deactivate the user's active card on the controller and close its active history link |
| `POST` | `/stations/{station_id}/users/{user_id}/cards/{assignment_id}/activate` | Reactivate a previously assigned card for its previous user |
| `POST` | `/stations/{station_id}/users/{user_id}/cards/adopt` | Optional: link an existing cloud station-card assignment to a user without enrolling it again |

Enrollment start request:

```json
{
  "device_id": 1,
  "timeout_seconds": 90
}
```

Poll until status is `captured`, then confirm. The captured UID is available as `card_number`.

Example confirmation request:

```json
{
  "card_type": "general",
  "is_valid": true,
  "valid_from": "2026-11-14",
  "valid_until": "2037-12-31",
  "door_indices": [0],
  "time_section_indices": [0]
}
```

`card_name` is optional. If omitted, the backend now uses the captured card UID as the card name. The person's name is stored separately on the station-user record.

Enrollment session statuses: `waiting`, `captured`, `confirming`, `confirmed`, `expired`, and `cancelled`.

### 7.2 Card reactivation behavior

The activation endpoint requires `assignment_id` to be the **`station_card_assignment_id`** from the card-history response (not the history row `id`). It only reactivates a card that was previously linked to that same station user. It:

- Keeps the existing physical card record and card UID.
- Preserves the old inactive history row and its `ended_at` timestamp.
- Creates a new active history link.
- Re-enables the card on the Dahua controller using its saved validity dates, type, door indexes, and time sections.
- Does not silently extend expired validity dates or change door/time permissions.
- Returns `sync_status: "pending_verification"`; inventory must be checked afterwards.

Example:

```text
POST /stations/1/users/1/cards/1/activate
```

No request body is required. If the card is already active, assigned to another user, missing its controller record number, outside its validity window, or belongs to a different user, the backend rejects the request.

## 8. Controller inventory verification and recovery

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/devices/{device_id}/inventory-check` | Compare database card UIDs with records read from the controller |
| `GET` | `/devices/{device_id}/sync-jobs` | Administrative history of inventory/reprovision jobs |
| `POST` | `/devices/{device_id}/reprovision` | Controlled recovery after a confirmed controller reset and required checks |
| `POST` | `/devices/{device_id}/reprovision/manual-verification` | Record the explicit manual-verification step in the recovery workflow |

Run inventory verification after enrollment, deactivation, or reactivation. The normal frontend should display `inventory_status`, expected/observed counts, missing cards and unexpected cards. Do not automatically delete unexpected physical records. Reprovisioning is an administrator recovery workflow, not a normal card action.

## 9. Access events

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/access-events` | List events; supports device, card, station, role, date, limit and offset filters |
| `GET` | `/access-events/summary` | Aggregate granted/denied/unknown counts |
| `GET` | `/access-events/{event_id}` | Read one event |

Events contain the controller access result and direction, card UID, device/station details, event time, and the station-user/operational-role snapshot when available. The optional `card_role` filter accepts legacy roles and operational role codes such as `CUSTOMER` or a custom role code.

Only a granted `ENTRY` event for an eligible, active, billable assignment at an active station qualifies for billing. Denied scans and non-entry events do not. Duplicate source events are deduplicated when the controller supplies a stable event key.

## 10. Rates, cash collections, dashboard and reports

### Rates and collections

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/stations/{station_id}/rates` | List station rates; optional `role=USER` or `role=STAFF` filter |
| `POST` | `/stations/{station_id}/rates` | Create a rate with an effective date range |
| `GET` | `/stations/{station_id}/cash-collections` | List cash collections; optional date filters |
| `POST` | `/stations/{station_id}/cash-collections` | Record a cash collection for a reporting period |

**Current billing model:** station-rate buckets are the legacy `USER` and `STAFF` values. Billable station users (including `CUSTOMER`) resolve to the `USER` rate bucket. The access-event worker snapshots the matching effective rate into `rate_applied` when an event is persisted. Configure a matching effective rate before expecting a billable event to have a non-null `rate_applied` value.

### Dashboard and reports

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/dashboard/summary` | Dashboard counters and totals |
| `GET` | `/dashboard/stations` | Station overview |
| `GET` | `/reports/usage` | Usage report for date range and optional station |
| `GET` | `/reports/card-usage` | Card-level usage report |

Use Swagger for the date-range and optional query parameter schemas on these report endpoints.

## 11. API routers removed in version 1.1.5

These routers are **not mounted** in the running FastAPI application. Their endpoints return HTTP 404 and do not appear in Swagger/OpenAPI:

- Legacy People and IC Cards router: `/persons/*` and legacy `/devices/{device_id}/cards/*` endpoints.
- Standalone Network router: `/api/network/interfaces`.

The `/device-initialization/interfaces` endpoint remains active and is the supported interface-list operation for the initialization/discovery wizard. The legacy source modules, database models, and migration helpers are retained in the package for compatibility with existing database tables; retaining those files does not expose their old HTTP routes.

One guarded maintenance route remains active: `POST /stations/{station_id}/cards/database-only-delete`. It deletes only unlinked/orphaned cloud card-assignment rows after the explicit `DELETE_DATABASE_ONLY` confirmation, refuses cards with any user-card history, preserves access-event rows, and never contacts the controller. It is for controlled database cleanup only and must not be placed in the normal frontend card-management UI.

## 12. Local development, configuration and deployment cautions

- Set the Next.js API base URL using an environment variable, not a hardcoded IP.
- For local development, the browser-visible host must resolve to the backend from the developer's machine. `127.0.0.1` means the same machine as the browser; it is not a production/cloud address.
- Use HTTPS/WSS in production.
- This package does not yet implement dashboard authentication, authorization, or enterprise/tenant isolation. Do not expose it publicly or connect multiple customer organizations before those controls are implemented.
- The WebSocket currently has no authentication/tenant filter. Do not treat a device ID query parameter as authorization.
- The device monitor and NetSDK sessions are process-owned. Run one API process for this starter; multiple Uvicorn workers would each start their own monitor/session manager.
- Keep `.env`, the database, and `data/device_secret.key` backed up. The database and encryption key must remain paired; replacing the key can make stored device passwords unreadable.

---

**Frontend integration priority:** device setup and registration → live device status → station assignment → roles/users → RFID enrollment/card lifecycle → inventory → access events → rates/cash/reporting.


## 13. Version 1.1.5 card reactivation compatibility fix

The card update/reactivation path now uses the same unfiltered ACCESSCTLCARD inventory query pattern as the working controller inventory listing. It matches the stored controller record number and RFID UID locally before applying `RECORDSET_UPDATE`. This avoids the card-number-filtered `FindRecord` query that returned `The device does not support current operation` on the reported ASI1201E. Reactivation continues to update the existing physical record; it does not insert a duplicate card. After reactivation, run inventory verification and physically test the card. The physical controller must still be tested because an offline SDK mock cannot guarantee firmware acceptance of `RECORDSET_UPDATE`.


## Door Sensor Configuration (v1.1.6)

The controller door sensor is configured on the physical Dahua device, not merely in the application database.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/devices/{device_id}/door-config` | Read the controller's current door sensor setting |
| PUT | `/devices/{device_id}/door-config` | Enable or disable the physical door sensor and verify by readback |

PUT body:
```json
{
  "sensor_enabled": true,
  "door_index": 0
}
```

`door_index` is zero-based; the ASI1201E single-door controller uses `0`. The backend uses Dahua CGI `configManager.cgi` with HTTP Digest authentication. The HTTP port defaults to `80` and can be changed using `DAHUA_HTTP_PORT`.

The PUT endpoint changes only `AccessControl[0].SensorEnable`; it does not modify unlock duration, door mode, alarm settings, or other door parameters. A successful response requires a subsequent GET readback matching the requested value. If the controller does not expose this CGI property, the API returns HTTP 502 rather than claiming success.

The frontend should load the current value with GET when opening device Door Parameters, then call PUT when the operator saves the switch. Show the returned `verified` flag and refresh the GET value after saving.
