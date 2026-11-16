# Changelog

## Version 1.1.4 — API surface cleanup

- Unmounted the legacy People and IC Cards router.
- Unmounted the standalone Network router.
- Kept `/device-initialization/interfaces` available for device discovery.
- Retained legacy data models and database migration helpers for database compatibility.

## 1.1.3 — Existing station-user card reactivation and frontend handoff

- Added `POST /stations/{station_id}/users/{user_id}/cards/{assignment_id}/activate` to reactivate the same controller card record for its previous station user.
- Preserved the old inactive user-card link and created a new active history link on reactivation.
- Kept the card's original validity dates, card type, door indexes and time-section indexes; reactivation does not silently extend validity or change access permissions.
- Added controller update, database uniqueness checks and pending inventory verification to the reactivation flow.
- Changed station-user RFID enrollment's default card display name to the captured card UID when `card_name` is omitted.
- Added a frontend API handoff document based on the routes and schemas in this project.
- Added guarded database-only cleanup for orphaned station-card rows; it refuses rows with card-history links and preserves access events.
- Added an access-event role filter that accepts predefined and custom operational role codes.
- Added offline smoke-test coverage for UID-based card names and reactivation.

### Verification scope

The new route and card-history behavior are covered by an offline test using a mocked Dahua SDK boundary. This does not perform a physical ASI1201E write/readback or lock test. After deployment, run `POST /devices/{device_id}/inventory-check` and physically test the reactivated card.


## 1.1.0 — Station users, operational roles and user-bound RFID enrollment

- Added four predefined station operational roles: MANAGER, ADMIN, STAFF and CUSTOMER.
- Added station-scoped custom operational roles with safe deactivation and protection for predefined roles.
- Added named station users with role assignment and an optional billability override.
- Added historical user-to-card assignment links with database-enforced one-active-card-per-user and one-active-user-per-card rules.
- Added user-bound RFID scan, poll and confirmation endpoints using the existing Dahua event listener and card CRUD service.
- Added adoption of an existing cloud station-card assignment into a named station user without re-enrolling the physical card.
- Prevented station-user enrollment tokens from being polled or confirmed through the legacy person-based enrollment endpoints.
- Added user and operational-role snapshots to access events; billable events resolve through the current station-user assignment.
- Preserved legacy people/card APIs and station-card storage for compatibility.
- Added additive SQLite/PostgreSQL-compatible schema setup, idempotent predefined-role seeding, offline API smoke tests and a pilot-database migration test.

### Verification scope

Automated tests use temporary SQLite databases and mocked Dahua SDK card insert/update operations. The included tests do not connect to a physical ASI1201E. A physical card scan, controller readback and door-unlock test remain required on the target device.


## 1.1.2 — Explicit controller-only card deletion

- Added `DELETE /devices/{device_id}/cards/device-records/{record_number}` for removing a physical Dahua card record when its cloud assignment has already been removed.
- Requires the exact controller card number and record-specific confirmation (`DELETE_CONTROLLER_CARD:{record_number}:{card_number}`).
- Reads and verifies the exact record before deletion; refuses if a matching legacy or station assignment remains in the application database.
- Leaves application assignments and access-event history untouched; marks device inventory `unknown` after the hardware operation so it must be checked again.
- Added regression coverage for confirmation enforcement, exact record matching, and database preservation.
