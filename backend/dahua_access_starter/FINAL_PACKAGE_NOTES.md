# Final Package Notes — Backend 1.1.4

## What changed

- Unmounted the legacy People and IC Cards router. `/persons/*` and legacy `/devices/{device_id}/cards/*` routes are no longer available and no longer appear in Swagger.
- Unmounted the standalone Network router. `/api/network/interfaces` is no longer available and no longer appears in Swagger.
- Kept `/device-initialization/interfaces` active for the initial device setup and discovery workflow.
- Kept the other device, monitoring, WebSocket, station, station-user, card, inventory, access-event, finance, recovery, dashboard and reporting routers mounted.
- Retained the legacy models, source modules and database migration helpers to avoid deleting or migrating existing database records. The old routers are not imported or mounted by `app/main.py`.
- Updated the frontend handoff and generated the complete OpenAPI specification from the mounted FastAPI application.
- Added automated regression tests that verify the removed routes return HTTP 404 and required routes remain available.

## Validation performed

- Python bytecode compilation passed.
- Pytest suite: 4 passed.
- Offline database-only card cleanup test passed.
- Offline station-user workflow smoke test passed, including RFID enrollment, card deactivation/reactivation, history preservation and event-to-user/role resolution.
- Runtime OpenAPI inspection confirmed that the tags `People and IC Cards` and `Network` are absent; `/device-initialization/interfaces` and the other retained route groups remain.
- No physical Dahua hardware tests were run during this packaging step.

## Important replacement and backup notes

- Generated `.venv`, Python bytecode/cache folders and pytest cache are excluded. Run `install.bat` on the Windows backend PC to create the environment. The Dahua SDK wheel remains in `vendor/`.
- The uploaded ZIP did not contain the live `.env` or SQLite database. Keep the current live `.env` and database; do not overwrite them with package placeholders.
- `data/device_secret.key` is preserved byte-for-byte from the uploaded project. Keep the live database and its matching encryption key together. If the live installation has a different key, retain the live key rather than overwriting it.
- Stop the API before copying updated source files. Back up the database, `.env`, and matching encryption key first.
- Physical controller initialization, connect/disconnect, card insert/freeze/reactivation, inventory readback and lock behavior still require verification on the target ASI1201E.

## Frontend handoff

Share these frontend-specific files with the Next.js developer:

- `docs/NEXTJS_FRONTEND_API_HANDOFF.md`
- `docs/openapi-frontend-v1.1.4.json`

Do not share the full backend archive with the frontend developer; it contains backend source, the SDK wheel and a device encryption-key file.
