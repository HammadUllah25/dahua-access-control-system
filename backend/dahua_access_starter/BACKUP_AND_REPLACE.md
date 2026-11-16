# Apply backend version 1.1.4 safely

## Before replacing the backend

1. Stop the running Uvicorn process with `Ctrl+C`.
2. Make a backup of your complete current `dahua_access_starter` folder.
3. Back up these live files separately:
   - `data/dahua_access.db`
   - `data/device_secret.key`
   - `.env` (if present)
4. Extract the release ZIP and copy the updated project source into your existing backend folder, allowing source files to be replaced.
5. Preserve the live database, matching encryption key and `.env`. Do not overwrite them with package copies.

The database and device encryption key must remain paired. If the live installation has a different `device_secret.key`, keep the live key. Replacing it may make stored device passwords unreadable.

## Install and start

1. Open the updated project folder.
2. Run `install.bat` if dependencies need to be installed or refreshed.
3. Start the API with `run.bat`.
4. Open `http://127.0.0.1:8000/docs`.

## Confirm the retired API groups are removed

These groups must be absent from Swagger:

- People and IC Cards
- Network

These APIs should return HTTP 404:

- `GET /persons`
- `GET /api/network/interfaces`

This initialization API must remain available:

- `GET /device-initialization/interfaces`

The other device, monitoring, WebSocket, station, station-user, RFID, inventory, access-event, finance, recovery and reporting APIs remain mounted.

## Share with the Next.js developer

Share only:

- `docs/NEXTJS_FRONTEND_API_HANDOFF.md`
- `docs/openapi-frontend-v1.1.4.json`

Do not share the full backend archive. It contains backend source, the vendor SDK wheel and a device encryption-key file.

## Verification boundary

The updated API route surface and offline station-user/card workflow are covered by automated tests. The physical Dahua controller and lock still require on-site verification. Run inventory verification after card enrollment or reactivation and test with a physical card before relying on the change operationally.
