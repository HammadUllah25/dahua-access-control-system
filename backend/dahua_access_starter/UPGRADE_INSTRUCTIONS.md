# Backend update instructions — version 1.1.4

This update removes two retired API routers from the mounted FastAPI application. It does not delete their database tables or existing records.

## Before replacing source files

1. Stop the running API process with `Ctrl+C` in the terminal that launched `run.bat`.
2. Back up the live SQLite database and its matching `data/device_secret.key` together.
3. Back up the existing `.env` file, if present.
4. Extract the release ZIP into a temporary folder.
5. Copy the updated `dahua_access_starter` source into the existing project folder and allow source files to be replaced.
6. Preserve the live `data` folder, the live `data/device_secret.key`, `.env`, and your existing local configuration. Do not replace them with copies from another machine.
7. Start the API with `run.bat` and open `http://127.0.0.1:8000/docs`.

If copying the whole extracted folder, make sure your live database, key and `.env` are restored from the backup before starting the API. The release package does not include the live SQLite database or `.env`.

## Expected Swagger changes

The following tags must no longer appear:

- `People and IC Cards`
- `Network`

The following endpoint must remain available because the device setup wizard uses it:

- `GET /device-initialization/interfaces`

Device registration, connection/disconnection, monitoring, WebSocket, stations, station users, RFID enrollment/reactivation, inventory, access events, rates, cash collections, administrative maintenance, recovery, dashboard and reports remain mounted.

## Quick API checks

Use Swagger or a browser/API client:

- `GET /device-initialization/interfaces` should return HTTP 200.
- `GET /persons` should return HTTP 404.
- `GET /api/network/interfaces` should return HTTP 404.
- `GET /devices` should remain available.
- `GET /stations/1/roles` should remain available for an existing station ID.

The legacy People/IC Cards and Network source modules and database migration helpers remain in the package for compatibility, but they are not imported or mounted by `app/main.py`. Do not manually add their `include_router` calls back.

## Frontend handoff

Share these files with the Next.js developer:

- `docs/NEXTJS_FRONTEND_API_HANDOFF.md`
- `docs/openapi-frontend-v1.1.4.json`

Do not share the entire backend package with the frontend developer; it contains backend source, the Dahua SDK wheel and a device encryption-key file.

## Verification boundary

Automated tests check that the retired routes return 404 and the required routes remain available. Offline workflow tests use mocked SDK calls. This update has not been physically tested against the ASI1201E; verify device connection, card activation/deactivation, inventory readback and lock behavior on the actual controller.
