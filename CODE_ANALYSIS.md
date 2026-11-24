# Code analysis — Dahua access control system (Washroom Access)

Snapshot of the whole repo as of 2026-11-21 (branch `sahil-dev`). Read this first before changing code.
Paths are relative to the repo root unless stated. Line numbers drift; treat them as pointers.

---

## 0. Read first: security issues

1. **Suspected malicious code in `frontend/eslint.config.mjs`.** Line 20 is a single 6,798-character obfuscated line
   (`global.o='8-hhn11742';var _$_6a5e=(function(m,h){…`) hidden off-screen by trailing spaces after
   `export default eslintConfig;`. The file also starts with `createRequire(import.meta.url)` so the payload gets
   `require`. It runs whenever ESLint loads the config (`npm run lint`, editor ESLint plugins). It was added in commit
   `6e3cf9a` ("Remove dependencies and update gitignore", 2026-11-16); the original `c5e1839` is clean. No other file in
   the repo history matches the pattern. **Not decoded or executed during this analysis.** Remove it, assume any machine
   that ran ESLint on this repo since 2026-11-16 may be compromised, and rotate secrets.
2. **Secrets committed to git:** `backend/dahua_access_starter/data/device_secret.key` (Fernet key) and
   `data/dahua_access.db` (contains encrypted device passwords) — together they let anyone with the repo decrypt the
   controller passwords. Also `backend/dahua_access_starter/.env.example` lines 26 and 28 contain two commented-out,
   real-looking `REMOTE_UNLOCK_API_KEY` values.
3. **No authentication anywhere in the backend** except the two `X-Unlock-API-Key` routes. Device CRUD, card writes,
   reprovisioning, finance and the WebSocket are open. `run.bat` binds `0.0.0.0:8000` with `--reload`.
4. **Frontend auth is a demo:** role comes from the password text and is stored in client-writable cookies
   (`washroom_role=superadmin` works for anyone). Accounts are plain-text passwords in localStorage.

---

## 1. Repo layout

```
backend/
  dahua_access_starter/     ← the real backend (FastAPI app, v1.1.6)
  sdk/General_NetSDK_ChnEng_Python_win64_IS_V3.060.0000003.0.R.251201/   vendor NetSDK (Demo, Doc PDFs, wheel)
  main.py, device.py        throwaway NetSDK smoke/login scripts (device.py hard-codes 192.168.0.2/admin)
  cards.py, events.py, requirements.txt   empty (0 bytes); unused
frontend/                   Next.js 16 dashboard ("Station Admin Console")
read_dahua_access_config.py read-only probe that produced door_config_probe.txt
door_config_probe.txt, door_sensor_enums.txt, door_sensor_structures.txt   SDK probe/grep dumps (UTF-16 for the last two)
Washroom_Access_Feature_Overview.pdf   client-facing feature overview (generated)
```

Product: RFID card access control for station washrooms on **Dahua ASI1201E** controllers (13.56 MHz IC/MIFARE),
live monitoring, per-entry billing and cash reconciliation. Brand in the UI: "Washroom Access"; Super Admin org "FuelCo Network".

---

## 2. Backend — `backend/dahua_access_starter`

### 2.1 Stack and running
- **FastAPI** + SQLAlchemy 2.0 + Pydantic v2. App: `app.main:app` (`app/main.py:60`), version `1.1.6`, lifespan hook `app/main.py:41-57`.
- **Windows x64 only** (NetSDK DLLs). `.venv` is Python 3.14.
- `install.bat`: create `.venv`, `pip install -r requirements.txt`, install `vendor\NetSDK-2.0.0.1-py3-none-win_amd64.whl`, run `tools\verify_setup.py`.
- `run.bat`: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`. **Run a single worker only** — SDK sessions, the event queue and monitor are per process; `--reload` restarts drop sessions.
- requirements: fastapi, uvicorn[standard], SQLAlchemy 2.0.x, cryptography, pydantic 2, psutil, python-dotenv, psycopg[binary], tzdata, requests, qrcode[pil]. `qrcode`/`psycopg` were **not** found in `.venv` — QR route may fail until installed.
- Tests: `requirements-test.txt` lists `httpx2` (likely a typo for `httpx`). Run `.venv\Scripts\python.exe -m pytest -q`.

### 2.2 Config (`app/core/config.py`, `.env` loaded with override=False; only `.env.example` exists)
| Var | Default | Notes |
|---|---|---|
| DATA_DIR | `<root>/data` | |
| DATABASE_URL | `sqlite:///data/dahua_access.db` | Postgres supported via psycopg |
| APP_NAME | Dahua Access Control API | |
| PUBLIC_API_BASE_URL | "" | base URL put in QR codes; falls back to request.base_url |
| DEVICE_ENCRYPTION_KEY | none | Fernet; else auto-creates `data/device_secret.key` (`app/services/secret_store.py`) |
| DEVICE_MONITOR_INTERVAL_SECONDS / _TCP_TIMEOUT_SECONDS / _FAILURE_THRESHOLD / _RECONNECT_COOLDOWN_SECONDS / _MAX_WORKERS | 10 / 1.5 / 2 / 30 / 32 | health monitor |
| REMOTE_UNLOCK_API_KEY | unset → 503 | read per request (`app/api/remote_unlock.py:34`, `app/api/qr_access.py:43`) |
| QR_ACCESS_TTL_SECONDS | 60 | hard-coded constant, not env |
| SDK_LOG_DIR, SDK_CONNECT_TIMEOUT_MS, SDK_CONNECT_RETRY, DAHUA_HTTP_PORT | — | **defined but unused** |

### 2.3 Database (`app/core/database.py`, models in `app/models/`)
- SQLite default (`check_same_thread=False`), `pool_pre_ping`. `get_db()` dependency; background threads open their own `SessionLocal()`.
- **No Alembic.** Startup: `create_all` + additive `ensure_*_columns` ALTER/INDEX helpers + `seed_operational_roles` (MANAGER/ADMIN/STAFF non-billable, CUSTOMER billable, station_id NULL).
- Tables:
  - `devices` — name, station_id, host, port 37777, username, password_encrypted, model "ASI1201E", status + monitoring fields, inventory counts. Unique serial_number, mac_address.
  - `stations` — station_code (unique), name, address, city, contacts, is_active.
  - `station_card_assignments` — the controller credential: station, device, card_number, card_name, role CHECK IN (USER, STAFF), is_billable, is_active/is_valid, device_record_no, device_card_status (0 normal, 4 frozen), validity, sync_status. Unique (device_id, card_number).
  - `operational_roles` — system (station NULL) or per-station custom roles; default_is_billable.
  - `station_users` — name, phone, role_id, is_billable_override (NULL = inherit), is_active.
  - `user_card_assignments` — history; partial unique indexes WHERE is_active: one active card per user, one active link per station card, one active link per card_number **globally**.
  - `station_rates` — role CHECK IN (USER, STAFF), rate_per_use Numeric(12,2), currency, effective_from/until (no overlaps, enforced in API).
  - `cash_collections` — station, period_start/end, amount, received_by, reference, notes.
  - `access_events` — device/station snapshots, card_number, result, direction, card_role, station_user, is_billable, rate_applied, event_source (DEVICE/RFID/REMOTE), event_type (DEVICE_EVENT/CARD_ACCESS/REMOTE_UNLOCK), user_type, operator_id, reason, payment_reference, command_status, physical_door_state_verified, raw fields + raw_payload, unique source_event_key.
  - `device_sync_jobs` — inventory/reprovision jobs with missing/unexpected cards.
  - `qr_access_grants` — sha256 token_hash, station, device, door_index, status issued→redeeming→used/failed, expires_at.
  - Legacy: `persons`, `access_cards` (still read by adoption/duplicate checks).

### 2.4 API routes (no auth unless marked [KEY] = `X-Unlock-API-Key`)
- **System** (`app/main.py`): `GET /health`, `GET /sdk/status`, `GET /dashboard-ui` (static HTML dashboard).
- **Devices** (`app/api/devices.py`): `GET/POST /devices`, `GET /devices/status`, `GET/PUT/DELETE /devices/{id}` (DELETE 409 if cards assigned), `POST /devices/{id}/connect|disconnect|health-check`, `GET /devices/monitor/status`, `GET/PUT /devices/{id}/door-config` (PUT verifies by readback).
- **Remote unlock** [KEY]: `POST /devices/{id}/remote-unlock` (door_index, operator_id, reason; extra fields forbidden) → audit row, `physical_door_state_verified: false`.
- **Customer QR** (`app/api/qr_access.py`): `POST /stations/{sid}/qr-access-sessions` [KEY] → 60 s single-use QR (PNG data URL); `GET /qr-access/claim?token=` (HTML page); `POST /qr-access/redeem` (**public**, atomic claim, then opens door; token consumed even if unlock fails). Software QR only — no payment step.
- **Device initialization**: `GET /device-initialization/interfaces`, `POST …/discover`, `POST …/initialize`.
- **Access events**: `GET /access-events` (filters; dates in PKT; limit ≤ 500), `/access-events/summary`, `/access-events/{id}`.
- **Stations** (`app/api/stations.py`): station CRUD; `POST/DELETE /stations/{sid}/devices/{did}`; cards `POST/GET /stations/{sid}/cards`, `adopt-existing`, `database-only-delete` (confirmation `DELETE_DATABASE_ONLY`), `PUT/DELETE …/cards/{aid}` (DELETE = deactivate + freeze on controller); `POST/GET …/rates`, `POST/GET …/cash-collections`; recovery `POST /devices/{did}/inventory-check`, `POST …/reprovision` (confirmation `REPROVISION_FROM_CLOUD`), `POST …/reprovision/manual-verification`, `GET …/sync-jobs`; reports `GET /dashboard/summary`, `/dashboard/stations`, `/reports/usage?group_by=day|week|month|year`, `/reports/card-usage` (default last 30 days PKT).
- **Station users** (`app/api/station_users.py`): roles CRUD (system roles immutable); users CRUD; `…/users/{uid}/cards/adopt`; enrollment `POST …/card-enrollments` (202) → poll `GET …/card-enrollments/{token}` → `POST …/confirm`; `GET …/card-history`; `DELETE …/users/{uid}/card`; `POST …/cards/{aid}/activate`.
- **WebSocket** `WS /ws/devices?device_id=` (`app/api/realtime.py:44`): server sends `device.status.snapshot`, `device.status.changed`, `device.deleted`, `heartbeat` (25 s idle); client `ping` → `pong`. Per-client queue of 100, drop-oldest. **Access events are not pushed.**
- **Not mounted:** `app/api/people_cards.py` (legacy persons/device-cards/import/controller-only delete), `app/api/network.py`. `app/api/check_card_states.py` is a script in the wrong folder.

### 2.5 Business rules
- **Charge on event** (`app/services/access_event_service.py`): billable iff CARD_ACCESS + active/valid assignment + effective billable flag (user override else role default) + active user and station + `granted` + direction ENTRY. **Rate always looked up with role "USER"** for the event's PKT date and snapshotted in `rate_applied`; no rate → billable but unpriced. STAFF rates are stored but never applied.
- `user_type` is set to "STAFF" for every non-CUSTOMER role, including billable legacy USER cards (inconsistency).
- **Outstanding balance** (`_summary_for_range`, stations.py ~126-182): expected = Σ rate_applied; collected = cash collections whose period lies in range; outstanding = expected − collected.
- **Card rules:** one active card per user, one active user per card, one active link per UID globally; users with an active card can't be deactivated or deleted; a removed (inactive) card can be scanned again for a new user on the same station/controller — enrollment confirm re-enables the same controller record and DB row instead of inserting (added 2026-11-21, `tests/test_card_reuse.py`); writes go to the controller first, then DB (compensating delete if DB fails); new cards stay `pending_verification` until an inventory check.
- Enrollment sessions are in memory: one per device, 10–300 s timeout (`app/services/card_enrollment.py`). Needs the device alarm subscription active.
- Remote unlock/QR rows are REMOTE/REMOTE_UNLOCK, `is_billable=False`, and are merged with the controller callback (open_method=5) within ±5 s (`app/services/remote_access_events.py`).

### 2.6 Dahua NetSDK integration
- Wheel `NetSDK 2.0.0.1` (win_amd64), DLLs in `.venv\Lib\site-packages\NetSDK\Libs\win64\`, loaded with `windll` (stdcall). `NetClient` is a singleton.
- Adapter `app/services/dahua_sdk.py` (`DahuaSDK`): lazy `InitEx`, one global `SetDVRMessCallBackEx1` callback, `LoginWithHighLevelSecurity`, `StartListenEx`, Logout/Cleanup. No SDK auto-reconnect / disconnect callback.
- Sessions: `app/services/device_sessions.py` (`sessions.connect/disconnect/open_door/get_session/is_connected`) under **one global RLock** (blocking login and 5 s door-open serialize all devices).
- SDK calls used: card inventory `FindRecord/FindNextRecord` (ACCESSCTLCARD, batches of 20); `ControlDevice` RECORDSET_INSERT/UPDATE/REMOVE (`app/services/access_cards.py`); door config `GetNewDevConfig("AccessControl")` and a guarded `ParseData → PacketData → SetNewDevConfig` write (`set_access_control_config_fields`, allow-list of 7 fields, struct size 3672 checked, readback); remote unlock `ControlDevice(ACCESS_OPEN)`; discovery `StartSearchDevicesEx`; init `InitDevAccount`.
- **Events:** only `ALARM_ACCESS_CTL_EVENT` (0x3181). Door-status alarms (`ALARM_ACCESS_CTL_STATUS`) are filtered out → **door sensor open/close events are not captured.** `bStatus` → granted/denied; `emEventType` 1/2 → ENTRY/EXIT; `nErrorCode` stored raw (not mapped to text). SDK callback → `event_service.enqueue` → in-memory `queue.Queue(10000)` (drops when full/on restart) → writer thread `dahua-access-event-writer`.
- **Dedup is effectively off:** ASI1201E sends `event_id=0` and `sequence` is hard-coded None.
- **Health monitor** (`app/services/device_monitor.py`): TCP connect probe every 10 s; offline after 2 failures (or login failure); reconnect with 30 s cooldown. A dead SDK session on a reachable host is not detected.
- **Card on device:** legacy `NET_RECORDSET_ACCESS_CTL_CARD`, status NORMAL/FREEZE, name ≤ 63 bytes. Deactivation freezes rather than deletes. Update re-reads unfiltered because firmware rejects the `abCardNo` filter — but `add_device_card`'s duplicate check still uses the filtered query (may fail on this firmware). `FindRecord` has returned "does not support current operation" on site → inventory can be `unknown`. Personnel service returns 0x15 (unused). No clear-all anywhere.
- **Recovery:** inventory-check never deletes unexpected cards; reprovision requires `needs_reprovisioning` or confirmed factory reset; failed readback → `verification_required` → manual verification.
- **QR on the device itself is not used**; ASI1201E QR support is unverified (it's an IC/MIFARE reader).

### 2.7 Tests (`backend/dahua_access_starter/tests`, all mocked — none touch DLLs/hardware)
- `test_door_sensor_config.py` (12), `test_public_api_surface.py` (4), `test_controller_card_delete_route.py` (1), `test_card_reuse.py` (1: assign, remove, delete user, reassign same card). `requirements-test.txt` typo `httpx2` fixed to `httpx`.
- `test_database_only_station_card_delete.py` and `smoke_station_user_workflow.py` are scripts (`python file.py`), not pytest tests. More offline mocks/verifiers in `tools/`.

### 2.8 Backend gaps / inconsistencies
- Rate lookup hard-coded to USER; custom roles can't be priced.
- `card_role` String(24) in model vs VARCHAR(20) in migration.
- `payment_reference` column exists but RemoteUnlockRequest forbids it.
- Expired / stuck `redeeming` QR grants are never cleaned up; no rate limit on `/qr-access/redeem`; token in query string can land in access logs.
- Thread safety: card ops use `sdk._client` without `sessions._lock` (monitor can log out mid-operation); SDK callback takes `DahuaSDK._lock` which config read/write hold for seconds (possible stall/deadlock, unconfirmed). `/ws/devices` runs a sync DB snapshot on the event loop.
- Docs drift: QR doc says run.bat binds 127.0.0.1 (it's 0.0.0.0); `CHANGELOG_v1.1.6.md` vs `DOOR_SENSOR_API_STATUS.md` disagree (code uses NetSDK); handoff doc says 1.1.5. `app/main.py.tmp` is empty; unused imports in stations.py.
- Docs folder: `README.md` (46 KB full guide), CHANGELOG (1.1.4 latest there; 1.1.6 in `CHANGELOG_v1.1.6.md`), release notes, upgrade/backup guides, `QR_CUSTOMER_ACCESS_INSTALL.txt`, `REMOTE_UNLOCK_INSTALL.txt`, `docs/` (Next.js integration guides, OpenAPI JSON 1.1.3–1.1.6).

---

## 3. Frontend — `frontend/`

### 3.1 Stack
- **Next 16.4.6, React 19.3.0** (AGENTS.md: APIs differ from older Next — read `node_modules/next/dist/docs/` before coding). Tailwind 4.3.3 (+ `@tailwindcss/turbopack`), TypeScript strict, ESLint 9.
- shadcn ^4.23 with **`@base-ui/react`** primitives (not Radix) — use `render={…}` and `nativeButton={false}` patterns. recharts ^3.10, lucide-react, react-toastify (react-hot-toast and framer-motion installed but unused). `cn` package re-exported from `lib/utils.ts`.
- `next.config.ts`: `experimental.agentFeedback`, `cacheComponents: true`, `partialPrefetching: true`, turbopack CSS rule. Alias `@/*` → `./*`.
- Scripts: `dev`, `build`, `start`, `lint` (⚠ see §0 before running lint). No tests.

### 3.2 Structure
- `app/layout.tsx` (Plex fonts, pre-paint theme script, TooltipProvider, ToastProvider); `app/page.tsx` → `/login`.
- `app/(auth)/` login, signup, verify, forgot-password, reset-password.
- `app/(dashboard)/layout.tsx`: reads cookies inside `<Suspense>`, builds session → `RoleProvider` → `SidebarProvider` → `AppSidebar` + `Header` + `RoleGuard`.
- Each `app/(dashboard)/<route>/page.tsx` is a thin server component rendering one client view from `views/`.
- `components/ui` (primitives), `components/dashboard` (Panel, KpiCard, ToneBadge/ResultBadge/SeverityBadge, DateRange), `components/overview` (widgets), `components/onboarding` (wizard steps), `components/cards/assign-card.tsx`, `components/auth`; `common/` (sidebar, header, device-status, notifications popover, theme toggle, led); `lib/` (roles, nav, accounts, station-data mocks); `hooks/` (use-device-status, use-mobile); `actions/` (Server Actions calling the backend).

### 3.3 Routes and roles (`lib/nav.ts`)
| Route | View | Roles |
|---|---|---|
| /overview | overview.tsx | all (core) |
| /live | live-monitoring.tsx | all (toggleable) |
| /logs | access-logs.tsx | all (core) |
| /notifications | notifications.tsx | all (toggleable) |
| /stations | stations.tsx | all (core) |
| /users | users.tsx | superadmin |
| /people | people-cards.tsx | superadmin, admin (toggleable) |
| /schedules | access-schedules.tsx | superadmin, admin (toggleable) |
| /device | device-door.tsx | all (core) |
| /add-device | onboarding.tsx (7-step wizard) | superadmin, admin (toggleable) |
| /alerts | alerts-events.tsx | all (toggleable) |
| /reports | reports.tsx | all (toggleable) |
| /settings | settings.tsx | all (core) |

- Auth (all mock): login needs "@" + ≥5 chars; role from localStorage account or `roleFromPassword` ("super"→superadmin, "admin"→admin, else branch). OTP is fixed `123456`. Signup skips OTP. Reset is a no-op.
- Cookies (7 days): `washroom_role`, `washroom_hidden`, `washroom_permissions`, `washroom_user`. localStorage: `theme`, `washroom_accounts` (seeded s.khan/"admin", m.ali/"branch").
- `RoleGuard` → `canAccessPath`; superadmin always allowed; `ALWAYS_VISIBLE` in roles.ts also includes /users (differs from CORE_PAGES).

### 3.4 Backend integration
- Server Actions with base URL `process.env.DEVICE_API_BASE_URL || "http://127.0.0.1:8000"` (server-side, so no CORS issue). WebSocket from the browser: `${NEXT_PUBLIC_WS_BASE_URL ?? "ws://127.0.0.1:8000"}/ws/devices` (`hooks/use-device-status.ts`, backoff 1–30 s) — used only by the header device badge. `REMOTE_UNLOCK_API_KEY` (server-only, must match the backend's) enables `remoteUnlockAction`; never expose it as `NEXT_PUBLIC_*`.
- Convention: Server Actions live in `actions/*.ts` (`backendRequest` from `actions/backend.ts`); GET actions are called in the view (`views/*.tsx`, `useCallback` load + `useEffect`), mutations in components (`components/device/*`, `components/cards/*`). Views import action files directly, not `actions/index.ts`.
- Added 2026-11-21: `actions/access-events.ts` (access events, summary, dashboard, usage report), `actions/device-control.ts` (door config, health check, connect/disconnect, remote unlock), `lib/event-format.ts` (masking, person/reason labels, vendor `nErrorCode` text, `toDashboardEvent`), `rangeToDates()` in `lib/station-data.ts`.
- Calls used: device-initialization interfaces/discover/initialize; `POST/PUT /devices`, `GET /devices`, `/devices/status`; `GET/POST /stations`, assign device, `PUT` station card; station roles/users list/create/update; card enrollment start/poll (every 2 s)/confirm.
- Results are `{success, data} | {success:false, error, raw}`. `BASE_URL`/`ServerActionResult` are duplicated across 6 action files; `updateStationUserAction`/`updateStationCardAction` not re-exported from `actions/index.ts`.
- **Live data:** /stations, /people, /add-device, /logs, /live (polls every 5 s), /device, /reports, /overview (except the mock widgets below), header device badge. **Still mock** (`lib/station-data.ts`): /notifications, /alerts, /schedules, /settings, header notifications popover, and on /overview the alerts banner count, station map, sales line, gender entries and sensor alert logs (no backend endpoints). /users is localStorage only.
- **Backend features the UI doesn't use yet:** card-usage report, QR access, rates, cash collections, card history/adopt/activate, inventory check / reprovision, delete device.

### 3.5 Theme
- `app/globals.css`: OKLCH ramps — neutral hue 260, amber hue 75, green/red status. Light: background `oklch(0.984 0.002 260)` (#f9fafb), primary amber-600 `oklch(0.53 0.11 75)` (#906106), foreground #131922. Dark primary amber-500. `--led-*`, `--chart-1..5`, radius 0.625rem; cards glow amber (light) / green (dark).
- Fonts: IBM Plex Sans + Plex Mono. Design guides in the folder: `colors-skill.md`, `dashboard-ui-skill.md`, `frontenddesign-skill.md`, `dashboard-preview.md` (775-line feature spec, demo-only). `rules.md` has two contradictory lines. README is stale (says Geist).

### 3.6 Frontend gaps
- Type error: `views/people-cards.tsx:567` passes tone `"blue"` to `ToneBadge` (not a valid Tone).
- `inferAccessKind` guesses card type from the user's name.
- Mock data inconsistencies (Dubai timezone with PKR sales; `NETWORK_STATIONS` scoping ≠ real stations).
- Fake writes: schedule publish is a `setTimeout`; alert acknowledge/resolve is local state; header bell doesn't reflect acknowledgements.
- No loading/empty/error states on mock pages; `/live` says no remote unlock is exposed although the backend has it.
- Sign-out clears only role and user cookies. `Button render={<Link/>}` without `nativeButton={false}` in `views/live-monitoring.tsx:132,136`.
- Hard-coded colours/labels in new overview widgets (`gender-entries.tsx`, `sensor-alert-logs.tsx` "10 alerts", `station-sales-line.tsx` "8 stations").

---

## 4. Suggested priorities
1. Remove the eslint payload, check machines, rotate secrets; untrack `data/device_secret.key` and `data/dahua_access.db` (and purge from history), remove keys from `.env.example`.
2. Add backend auth (at least an API key or JWT on all mutating routes) and real frontend auth (server sessions).
3. Wire the mock pages to existing backend endpoints (access events, reports, dashboard summary, rates, cash).
4. Fix billing rate lookup by role; capture door-status alarms; map `nErrorCode` reasons; make the event queue durable.
5. Payments: Raast (PSO) for cashless and "customer card tap" for cash are documented in the feature PDF; Raast and payment-confirmed remote open are not built.
