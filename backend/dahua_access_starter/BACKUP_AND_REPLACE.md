# Replace the Dahua backend safely

This package updates the backend starter while retaining the existing API modules for device initialization, registration, monitoring, people, and cards.

## Before replacing

1. Stop the running Uvicorn process.
2. Make a copy of your current `backend/dahua_access_starter` folder.
3. Keep your existing `.env` file, `data/dahua_access.db`, `data/device_secret.key`, and `venv`. This archive intentionally does **not** contain those files.
4. Extract this folder and merge its contents into your existing `backend/dahua_access_starter` folder, allowing the supplied source files to be replaced. Do not delete your `data` folder.

## Install/update dependencies

From `backend/dahua_access_starter` in PowerShell:

```powershell
..\venv\Scripts\python.exe -m pip install -r requirements.txt
```

The Dahua NetSDK wheel is not redistributed in this archive. Keep using the NetSDK wheel already installed in your existing virtual environment.

## Start the API

```powershell
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`.

## Added endpoints

- `GET /api/network/interfaces` — active Ethernet/LAN interfaces only.
- `GET /device-initialization/interfaces` — Ethernet IPv4 addresses used for local discovery.
- `GET /access-events` — newest-first stored access events; supports `device_id`, `card_number`, `limit`, and `offset`.
- `GET /access-events/summary` — total, granted, denied, and unknown counters for dashboard cards.
- `GET /access-events/{event_id}` — one stored event.
- `POST /devices/{device_id}/card-enrollments` — open a timed card-scan enrollment window.
- `GET /devices/{device_id}/card-enrollments/{session_token}` — poll for the captured card UID.
- `POST /devices/{device_id}/card-enrollments/{session_token}/confirm` — create the controller personnel profile, write the scanned card, and save the assignment.
- `DELETE /devices/{device_id}/card-enrollments/{session_token}` — cancel enrollment.

## Event listener behaviour

The NetSDK alarm listener uses `SetDVRMessCallBackEx1` plus `StartListenEx`, matching the vendor's `AlarmListen` sample and the `ALARM_ACCESS_CTL_EVENT` event structure. The native callback only copies event fields and enqueues them; a background worker writes them using independent SQLAlchemy sessions.

The vendor's `NET_A_ALARM_ACCESS_CTL_EVENT_INFO` structure documents `bStatus` as the card-scan result (`TRUE` = success, `FALSE` = failure). The backend stores this as `access_result` (`granted` / `denied`) and also retains raw `bStatus`, `emStatus`, and `nErrorCode` for audit/debugging.

All access-control event messages received by the SDK listener are stored. The enrollment flow captures the first message containing `szCardNo` after its scan window begins. Confirm requires the UID to match the application's hexadecimal IC UID format. Personnel profiles are added through `OperateAccessUserService` (`NET_ACCESS_USER_INFO`); the person's `person_code` is used as the device UserID and the optional UserID+password secret is transmitted to the controller only. It is not stored in SQLite or returned by the API.

**Physical-device verification is still required.** After deployment, test whether an unknown/unregistered card scan emits `ALARM_ACCESS_CTL_EVENT` with `szCardNo`; then test one personnel INSERT and one card insert with a spare card. Some firmware/configurations may not report unknown-card scans or may not implement every personnel service operation. The enrollment session will time out rather than invent a UID if no scan event arrives.

## Database safety

Startup migrations are additive: they add missing device identity columns and unique indexes without dropping existing tables or rows. The `access_events` table is created automatically. Enrollment sessions are in memory and need no schema migration. Back up your database before updating as a normal operational precaution.


## Next.js dashboard integration

See `docs/NEXTJS_DEVICE_STATUS_INTEGRATION.md` for the REST/WebSocket event contract, environment variables, reconnecting React hook, and example dashboard component. The backend monitor is independent of the browser connection and uses the defaults in `.env.example` (10-second interval, two consecutive failed probes before offline).

The API currently has no authentication layer. Keep it on a trusted LAN/VPN until authentication and authorization are implemented. Run one Uvicorn worker because NetSDK handles are process-local.
