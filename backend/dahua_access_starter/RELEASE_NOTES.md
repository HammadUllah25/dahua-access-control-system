# Release notes — Dahua Access Control Backend

## Version 1.1.4 — API surface cleanup

- Unmounted the legacy People and IC Cards router.
- Unmounted the standalone Network router.
- Kept `/device-initialization/interfaces` available for device discovery.
- Retained legacy data models and database migration helpers for database compatibility.

## Added

- Station registry and explicit device-to-station association.
- Station-scoped RFID card assignments with `USER` and `STAFF` roles and no required person record.
- Effective-dated PKR per-use rates; the applied rate is snapshotted when a billable event is persisted.
- Cash collection records with usage-period and cash-received timestamps.
- Dashboard summary, per-station overview, daily/weekly/monthly/yearly usage reports, card-wise usage and date-filtered event API.
- Built-in read-only HTML dashboard at `/dashboard-ui`.
- Device card inventory checks, sync-job audit records and administrator-confirmed reprovision from the cloud assignments.
- Safe adoption endpoint for existing person-based card records into station USER/STAFF assignments without deleting legacy records or enrolling duplicate hardware cards.
- Additive startup migration for station and billing fields on existing SQLite/PostgreSQL databases.
- Persistent `DEVICE_ENCRYPTION_KEY` support for a future multi-instance/cloud deployment.
- Dahua invalid-card update path uses the SDK's `FREEZE` status constant rather than leaving the card state `NORMAL`.

## Compatibility

The original person-based `/persons` and `/devices/{device_id}/cards` routers are not mounted in version 1.1.4. Their models and database migration helpers remain in the project to preserve compatibility with existing databases. Existing person-based card assignments are not automatically converted to station users because their operational role cannot be inferred safely.

## Validation completed

- Python bytecode compilation.
- Four pytest regression tests passed, including checks that the retired routers return 404 and required initialization routes remain available.
- Station role, event enrichment, rate snapshot, USER/STAFF billing and cash reconciliation smoke test.
- Mocked API flow for station/device association, station-card assignment, rates, cash collection, dashboard filters, unknown-inventory safety, and reset-reprovision state handling.
- FastAPI startup, dashboard route and OpenAPI generation.
- Additive migration against an existing SQLite schema.
- Dahua SDK ctypes/enum declaration checks and mocked card-update/initialization flows.

## Not validated on physical hardware

The build environment cannot load the Windows x64 Dahua native SDK DLLs or reach the ASI1201E. Card insert/freeze/readback/reprovision must be verified against the actual controller and firmware. The known ASI1201E `FindRecord` unsupported-operation response is handled as unknown inventory; it is never treated as an empty controller.

## Production gaps

This release is not yet a production-ready 100-station cloud deployment. It does not include authenticated multi-role users, a secure Windows site-agent/VPN architecture, automatic factory-reset detection, a durable event outbox/queue, or exactly-once accounting for ASI1201E events that arrive without a stable native sequence/event ID. The current dashboard is read-only; station/card/rate/cash management is through the API docs.
