# Replace the Dahua backend safely

This package updates the backend starter while retaining the existing API modules for device initialization, registration, monitoring, people, and cards.

## Before replacing

1. Stop the running Uvicorn process.
2. Make a copy of your current `backend/dahua_access_starter` folder.
3. Keep your existing `.env` file and `data/dahua_access.db` file. This archive intentionally does **not** contain either file.
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

## Event listener behaviour

The NetSDK alarm listener uses `SetDVRMessCallBackEx1` plus `StartListenEx`, matching the vendor's `AlarmListen` sample and the `ALARM_ACCESS_CTL_EVENT` event structure. The native callback only copies event fields and enqueues them; a background worker writes them using independent SQLAlchemy sessions.

The vendor's `NET_A_ALARM_ACCESS_CTL_EVENT_INFO` structure documents `bStatus` as the card-scan result (`TRUE` = success, `FALSE` = failure). The backend stores this as `access_result` (`granted` / `denied`) and also retains raw `bStatus`, `emStatus`, and `nErrorCode` for audit/debugging.

All access-control event messages received by the SDK listener are stored. After deployment, test a registered card and an invalid/unregistered card to confirm the device firmware sends both outcomes through this message callback.

## Database safety

Startup migrations are additive: they add missing device identity columns and unique indexes without dropping existing tables or rows. The `access_events` table is created automatically. Back up your database before updating as a normal operational precaution.
