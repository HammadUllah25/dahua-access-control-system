# Dashboard Preview — FuelCo Washroom Access Console

This document describes the complete dashboard as it exists in this frontend: the three roles, every page they can open, the content on each page, the features and actions available, and the rules that decide what each role sees.

> **Demo notice:** this is a frontend preview. Role selection, managed accounts and page permissions are mock implementations stored in cookies / `localStorage`. They demonstrate the intended role model, not production security.

---

## 1. Sign-in and role selection

### Auth pages

| Route | Purpose |
| --- | --- |
| `/login` | Email + password sign-in |
| `/signup` | Create a demo account |
| `/verify` | OTP verification (demo code `123456`) |
| `/forgot-password` | Request a reset |
| `/reset-password` | Set a new password |

The auth pages share a constant brand panel. The dashboard and Add Device flow use the dashboard chrome instead.

### How the role is chosen

The role comes from the password text, unless the email belongs to an account created in **Users & Roles**.

| Password contains | Role |
| --- | --- |
| `super` (anywhere) | **Super Admin** |
| `admin` (anywhere) | **Admin** |
| anything else | **Branch** |

- Login requires a password of at least 5 characters so `admin` works.
- Signup requires at least 8 characters.
- A role hint appears on login after 5 characters.
- Managed accounts take precedence. If an email exists in the account list, the password must match that account; the password text does not override the account's role.
- Emails not in the account list fall back to the demo password rule.

### Seeded demo accounts

| Name | Email | Password | Role |
| --- | --- | --- | --- |
| S. Khan | `s.khan@fuelco.example` | `admin` | Admin |
| M. Ali | `m.ali@fuelco.example` | `branch` | Branch |

The Super Admin account is built in and is not stored in the account list.

### Landing pages

- `/` redirects to `/login`.
- Any dashboard route without a role cookie redirects to `/login`.
- Login always lands on `/overview`.
- Signup lands Branch accounts on `/overview` and Admin/Super Admin accounts on `/onboarding`, which redirects to `/add-device`.
- `/onboarding` remains as an entry point but now redirects into the dashboard's Add Device page.

---

## 2. Role model at a glance

| | Super Admin | Admin | Branch |
| --- | --- | --- | --- |
| Workspace label | FuelCo Network | Area A | Branch 04 |
| Sidebar subtitle | Super Admin · all areas | Admin · area monitoring | Branch · station monitoring |
| Command centre | Network command centre | Area command centre | Branch command centre |
| Scope | All areas · all stations | Area A · area and station monitoring | Branch 04 · all branch stations |
| Stations visible | 6 | 4 (Area A) | 3 (Branch 04) |
| Default pages | All 12 | 11 (no Users & Roles) | 8 (monitoring + reports) |
| Create Admin/Branch accounts | Yes | No | No |
| Set page permissions | Yes | No | No |
| Customize dashboard modules | Yes | No | No |
| Station features | All | All station features | Monitoring features only |
| Default user | A. Rahman · `a.rahman@fuelco.example` | S. Khan · `s.khan@fuelco.example` | M. Ali · `m.ali@fuelco.example` |

### Station scope

| Station | Area | Branch | Status | Devices |
| --- | --- | --- | --- | --- |
| PumpStation 01 (ST-01) | Area A | Branch 04 | Online | 4 |
| PumpStation 02 (ST-02) | Area A | Branch 04 | Online | 2 |
| PumpStation 03 (ST-03) | Area A | Branch 05 | Offline | 3 |
| PumpStation 04 (ST-04) | Area A | Branch 04 | Online | 3 |
| PumpStation 05 (ST-05) | Area B | Branch 07 | Pending | 1 |
| PumpStation 06 (ST-06) | Area B | Branch 07 | Online | 2 |

- **Super Admin:** all 6 stations — 4 online, 1 offline, 1 pending, 15 devices.
- **Admin:** 4 Area A stations — 3 online, 1 offline, 12 devices.
- **Branch:** 3 Branch 04 stations — 3 online, 9 devices.

---

## 3. Shared dashboard shell

Every role gets the same console frame, filtered to its permissions.

### Sidebar

- Workspace name and role subtitle.
- Nav groups: **Operations**, **Network**, **People & access**, **Station**, **Insights**.
- Only groups with at least one allowed item are shown.
- Active route is highlighted.
- Collapsible to icons.
- Footer shows a green LED + **Monitoring active** and the role scope.

### Header

- Current section title.
- Role badge (Super Admin / Admin / Branch).
- **Realtime controller status** from the backend:
  - Initial snapshot from `GET /devices/status`.
  - Live updates from `ws://127.0.0.1:8000/ws/devices`.
  - Reconnect backoff 1 s → 30 s.
  - Goes offline on `device.deleted`.
  - No polling.
- Current date.
- Light/dark theme toggle.
- The header indicator is the one realtime Online/Offline source; page-level controller tiles still use mock data.

### Access control

- The dashboard layout reads the role, hidden modules, page permissions and user from cookies.
- `RoleGuard` checks the current path against role, hidden modules and permissions.
- A disallowed, hidden or denied route redirects to `/overview`.
- Core monitoring pages can never be hidden or denied.

### Visual language

- Amber/yellow accent palette; green, red, amber and grey are reserved for semantic status.
- Status is never shown by colour alone: LEDs and badges always carry a text label.
- Cards have a subtle hover glow; dark mode uses the green LED glow.
- Charts use amber for **Granted** and red for **Denied**.
- Relay command and physical door state are shown separately, with a note that a relay command is not proof the door opened.
- KPI cards link to pre-filtered pages where the data supports it.

---

## 4. Page access matrix

| Page | Route | Super Admin | Admin | Branch | Access type |
| --- | --- | :---: | :---: | :---: | --- |
| Overview | `/overview` | ✅ | ✅ | ✅ | Core — always visible |
| Live Monitoring | `/live` | ✅ | ✅ | ✅ | Optional — default on |
| Access Logs | `/logs` | ✅ | ✅ | ✅ | Core — always visible |
| Stations | `/stations` | ✅ | ✅ | ✅ | Core — always visible |
| Users & Roles | `/users` | ✅ | — | — | Super Admin only, not hideable |
| People & Cards | `/people` | ✅ | ✅ | — | Optional — default on for Admin |
| Access Schedules | `/schedules` | ✅ | ✅ | — | Optional — default on for Admin |
| Device & Door | `/device` | ✅ | ✅ | ✅ | Core — always visible |
| Add Device | `/add-device` | ✅ | ✅ | — | Optional — default on for Admin |
| Alerts & Events | `/alerts` | ✅ | ✅ | ✅ | Optional — default on |
| Reports | `/reports` | ✅ | ✅ | ✅ | Optional — default on |
| Settings | `/settings` | ✅ | ✅ | ✅ | Core — always visible |

**Default optional pages**

- **Admin:** `/live`, `/people`, `/schedules`, `/add-device`, `/alerts`, `/reports`.
- **Branch:** `/live`, `/alerts`, `/reports`.
- Branch can never be granted People & Cards, Access Schedules or Add Device: those pages are not available to the Branch role.
- Super Admin ignores page-permission restrictions but still respects globally hidden modules.

---

## 5. Page-by-page content

### 5.1 Overview — `/overview`

**Who sees it:** every role.

**Purpose:** the role's command centre: current station health, access KPIs, activity, map and recent events.

**Header and banners**

- Title changes by role: **Network command centre**, **Area command centre** or **Branch command centre**.
- Scope line: `All areas · 6 stations`, `Area A · 4 stations` or `Branch 04 · 3 stations`.
- Date range: **Today / 7 days / 30 days**, default **7 days**.
- Role scope banner: role label, scope, and a link to **Stations** showing `Monitor stations · N/M online`.
- System status banner:
  - **Operational** — controller online, no active critical alert.
  - **Attention required** — active critical alert.
  - **Offline** — controller connection lost.

**KPI row (5 cards)**

| KPI | Content | Link |
| --- | --- | --- |
| Total scans | All attempts including denied, for the selected range | `/logs` |
| Granted access | Granted count + change vs previous period | `/logs?result=Granted` |
| Denied access | Denied count | `/logs?result=Denied` |
| Success rate | Granted ÷ total attempts | — |
| Controller status | Online/Offline + last seen | `/device` |

**Charts and panels**

- **Access activity** — line chart of granted vs denied over the selected range.
- **Access outcomes** — donut of granted vs denied with total scans in the centre and a legend with counts and shares.
- **Station map** — see below.
- **Usage by hour** — bar chart of scan volume by hour of day.
- **Device & door status** — controller LED and state, model + serial, last seen, physical door contact, lock relay command, and the relay-command caveat. Links to `/device`.
- **Access rhythm** — custom recharts panel showing access patterns.
- **Denial reasons** — custom recharts panel showing the most frequent rejection reasons.
- **Recent access activity** — the 8 latest attempts: time, person, masked card, result, reason. Links to `/logs`.

**Station map**

- Keyless Google Maps embed centred on Sheikh Zayed Rd, Dubai, zoom 16.
- Theme-tinted map that follows light/dark mode.
- Three installed access points:
  - Washroom entry · Reader 1 — Online.
  - Washroom exit · Reader 2 — Online.
  - Shop staff door — Pending.
- Markers blink and include labels; status is written out in the side list.
- Markers are percentage overlays, so they stay in place while the map pans/zooms. Anchored markers need a keyed Google Maps JS API.

**Data:** deterministic mock access events covering 60 days, roughly 45–70 events per day, about 13% denied, five documented denial reasons.

---

### 5.2 Live Monitoring — `/live`

**Who sees it:** all roles by default; Super Admin can hide it; Admin/Branch can be denied it.

**Purpose:** the latest authentication stream and current door/controller state.

**Content**

- **Live** badge and controller state with last communication; warns when the feed is stale because the controller is offline.
- Filter: **All / Granted / Denied**.
- **Latest scans** feed (20 events): time, person or "Unresolved card", masked card, reason, result badge.
- **Door status** tile: physical contact state and whether the sensor is wired.
- **Controller** tile: online/offline, LED, model and serial.
- **Quick actions:** Open Access Logs, Open Device & Door.
- Note that no remote unlock action is exposed by default.

---

### 5.3 Access Logs — `/logs`

**Who sees it:** every role (core page).

**Purpose:** audit trail of every recorded authentication attempt, newest first.

**Content**

- Date range: Today / 7 days / 30 days, default 30 days.
- **Export CSV** of the filtered records.
- Filters:
  - Search by event ID, card number or person name.
  - Result filter: All / Granted / Denied.
  - Person filter: all people or one person.
- Records table: time, person, masked card, result, reason, device.
- Pagination: 25 rows at a time with **Show 25 more**.
- Row opens a detail drawer:
  - Event ID, timestamp, person, card, result, reason, device, door, controller model.
  - Card identifiers stay masked in list views.
- Supports pre-filtering from Overview KPIs via `?result=Granted` or `?result=Denied`.
- Empty state when no events match.

---

### 5.4 Stations — `/stations`

**Who sees it:** every role (core page), scoped to the role.

**Purpose:** monitor every station in the role's scope: controller health and reader count.

**Content**

- Header with role view and scope.
- Four KPIs:
  - **Stations** — count in scope.
  - **Online** — controllers reachable.
  - **Offline** — needs attention.
  - **Devices** — total devices, with pending-setup station count.
- **Station monitoring** table: station name + ID, area, branch, devices, status (Online/Offline/Pending), last seen.
- Super Admin sees 6, Admin sees 4, Branch sees 3.

---

### 5.5 Users & Roles — `/users`

**Who sees it:** Super Admin only. Not hideable, not grantable.

**Purpose:** create Admin and Branch accounts and decide which optional pages each role can open.

**Content**

- Three KPIs: **Accounts**, **Admins**, **Branch**.
- **Create an account** form:
  - Full name (minimum 2 characters).
  - Email (must contain `@`).
  - Temporary password (minimum 5 characters).
  - Role: Admin or Branch.
  - Duplicate email rejected.
  - Success toast names the new account and role.
  - Demo note: accounts are stored in this browser; share the email and password with the holder.
- **Page permissions** matrix:
  - Rows: Live Monitoring, People & Cards, Access Schedules, Add Device, Alerts & Events, Reports.
  - Columns: Admin, Branch.
  - A page that is not part of a role shows **Not available**.
  - Save permissions / Reset defaults.
  - Shows how many pages each role has selected.
  - Core pages and globally hidden modules are called out as unaffected.
- **Accounts** table:
  - Account name + email, role, scope, created date.
  - Delete action with confirmation and toast.
  - Empty state when no accounts exist.
  - The Super Admin account is built in and not listed.

**Effect of saving permissions**

- The sidebar, `RoleGuard` and direct-URL access all update after `router.refresh()`.
- Permissions apply per role, not per account: every Admin account shares the Admin page set, and every Branch account shares the Branch page set.

---

### 5.6 People & Cards — `/people`

**Who sees it:** Super Admin and Admin. Optional; on by default for Admin. Not available to Branch.

**Purpose:** people records and the card credentials that can authenticate at the washroom reader.

**Content**

- Header with **Add person** dialog:
  - Name.
  - Category: Normal / VIP / Guest / Patrol.
  - Assign as: Staff / Visitor.
  - Valid from / valid to dates.
  - Creates the person and a placeholder MIFARE card.
- Summary strip: Total people, Active cards, Expired cards, Blocked cards.
- **Directory**:
  - Search by name or card number.
  - Category filter: All / Normal / VIP / Guest / Patrol.
  - Role filter: All / Staff / Visitors.
  - Table: person, role, category, card, validity, card status.
- **Person detail drawer**:
  - **Admin assignment:** change the person between Staff and Visitor.
  - **Assigned credential:** card, technology (MIFARE 13.56 MHz), validity window, schedule, status.
  - **Card actions:** Block card, Deactivate, Activate.
  - If no card: enrollment prompt to present a MIFARE card at the reader.
- All changes are local state only; they are not pushed to the controller.

---

### 5.7 Access Schedules — `/schedules`

**Who sees it:** Super Admin and Admin. Optional; on by default for Admin. Not available to Branch.

**Purpose:** show and edit when a credential may use the washroom, in plain language instead of device time sections.

**Content**

- **Schedules** list: Staff hours, Extended (VIP), Guest daytime, Patrol night rounds, Cleaning crew early. Each shows its time range, days per week and sync state.
- **Weekly schedule editor**:
  - Day toggles (Mon–Sun).
  - Start and end time.
  - Door name.
  - Any edit marks the schedule **Pending**.
- **Preview** panel: "This card can access at …" summary of the edited schedule.
- **Publish** panel: sync badge and **Save & publish**. Publishing shows a syncing state and then marks the schedule **Synced**.
- **Credential validity** panel:
  - Select a person.
  - Show their card, validity window and schedule.
  - Distinguishes card validity from the daily time schedule.
- **Holiday calendar**: Commemoration Day, National Day, New Year, with the access period for each.
- Edits stay local; pushing to the controller needs the write API.

---

### 5.8 Device & Door — `/device`

**Who sees it:** every role (core page).

**Purpose:** whether the access-control hardware is connected and operating.

**Content**

- **Device summary**: LED + Online/Offline, model, serial, station, firmware.
- **Connection**: method, IP reference, client status, last seen.
- **Door & relay status**:
  - Door name.
  - Lock relay command.
  - Physical door contact.
  - Note that a relay command is not proof the door physically opened; physical state requires the wired contact sensor.
- **Sync status**: last successful sync, pending changes, sync errors.
- **Device event history**: heartbeat, config sync, offline, online, restart events.
- **Device configuration**: door name, device label, reader protocol.
- **Troubleshooting**: network reachability, SmartPSS Lite client, door contact wiring, last error, and a note that remote repair is not available.

> The page currently uses the mock controller record (`DEVICE.online: true`). Only the header badge uses real backend status.

---

### 5.9 Add Device — `/add-device`

**Who sees it:** Super Admin and Admin. Optional; on by default for Admin. Not available to Branch.

**Purpose:** register another Dahua controller without leaving the console.

**Flow: four steps**

1. **Network & Recovery**
   - Choose **Auto-Detected Interfaces** or **Enter IP Manually**.
   - Auto-detected mode calls the backend for local IPv4 interfaces, with a loader, retry and error state.
   - Manual mode accepts an IPv4 address, with validation and subnet suggestions.
   - Proceed validates the selected IP and the prefilled recovery contacts.
2. **Discover Devices**
   - Shows the local discovery IP and a wait time (2–15 seconds).
   - Auto-scans on entry; **Scan** reruns discovery.
   - Loading, error and empty states.
   - Found controllers are listed; selecting one continues.
   - Already-initialized controllers skip the initialize step.
3. **Initialize Device**
   - Username (minimum 3 characters), password and confirmation (minimum 8 characters, Dahua standard).
   - Calls the initialize endpoint.
   - If the backend's 5-minute discovery cache expired, it rediscovers once and retries automatically.
   - If the controller is already initialized, it continues to Connect.
4. **Connect Device**
   - Shows the controller summary: model, IP, MAC, serial, **Initialized** badge.
   - Form: device name, host, port (default `37777`), username, password.
   - Options: connect now, monitoring enabled.
   - Registers with `POST /devices`.
   - If the controller is already registered (`409`), it finds the existing record and updates its credentials with `PUT /devices/{id}`.
   - Success toast reports whether the controller is online or registered but not connected, including the backend error when present.
   - On success, goes to `/overview`.

**Backend:** local FastAPI at `http://127.0.0.1:8000`. All calls go through server actions, so the browser avoids CORS.

**Toasts:** every backend response is surfaced, including raw error text.

---

### 5.10 Alerts & Events — `/alerts`

**Who sees it:** all roles by default; optional.

**Purpose:** exceptions that may need attention.

**Content**

- Severity filter: All / Critical / Warning / Info.
- Summary counts: Active, Acknowledged, Resolved.
- **Alerts** table: time, event, device serial, severity, status. Row opens a drawer.
- **Notification preferences**:
  - In-app alerts.
  - Email digests, with a note that SMTP must be configured first.
- **Alert detail drawer**:
  - Event type, timestamp, device model + serial, full detail.
  - Severity and status badges.
  - Acknowledged-by line.
  - **Acknowledge** and **Resolve** actions.
  - Note that actor, timestamp and resolution are recorded in the audit log.
- Acknowledge/resolve is local state only for now.

**Seeded alerts:** door timeout, blocked card attempt, tamper detected, controller offline, intrusion (out of section).

---

### 5.11 Reports — `/reports`

**Who sees it:** all roles by default; optional.

**Purpose:** usage patterns and exportable records. Every block uses the same date range.

**Content**

- Date range: Today / 7 days / 30 days.
- **Export CSV** of daily granted/denied totals.
- **Usage trend** — stacked bar chart of granted vs denied per day.
- **Hourly usage** — scan distribution by hour, useful for staffing and cleaning planning.
- **Outcome breakdown** — granted and denied counts with their share of attempts.
- **Top usage periods** — the five busiest hours and the busiest day in the range.
- **Denial reasons** table — reason, count and share of denials with a bar.

---

### 5.12 Settings — `/settings`

**Who sees it:** every role (core page). Some panels are role-dependent.

**Content**

- **Role & scope**: role, scope and what the account can monitor/manage.
- **Station profile** (read-only): station ID `ST-04`, name `PumpStation 04`, address, contact. The description says station records are managed centrally.
- **Role profile**: name, email, role, new password + confirmation, **Update password** button. Role elevation is not permitted.
- **Display preferences**: timezone, date format, table density.
- **Security & sessions**: current browser session and another session with **Sign out**.
- **Integration**: controller model, serial, firmware, integration state (`Connected via SmartPSS Lite`), connection method, support reference. Secrets, keys and passwords are never shown.
- **Sign out** clears the role and user cookies and returns to `/login`.

**Super Admin-only panel — Dashboard customization**

- Toggle which optional modules appear for **every role**:
  - Live Monitoring
  - People & Cards
  - Access Schedules
  - Add Device
  - Alerts & Events
  - Reports
- Overview, Stations, Access Logs, Device & Door, Settings and Users & Roles always stay visible.
- Shows how many modules are hidden.
- **Reset modules** restores everything.
- Changes apply immediately after `router.refresh()`.

---

## 6. Role walkthroughs

### 6.1 Super Admin

**Workspace:** FuelCo Network · all areas.

**Default sidebar**

- **Operations:** Overview, Live Monitoring, Access Logs
- **Network:** Stations
- **People & access:** Users & Roles, People & Cards, Access Schedules
- **Station:** Device & Door, Add Device, Alerts & Events
- **Insights:** Reports, Settings

**What the Super Admin can do**

- See all 6 stations across Area A and Area B, and every branch.
- See network-wide Overview KPIs, access activity, map, denial reasons and recent activity.
- Monitor every station's health, device count and last-seen time.
- Review the full access-log audit trail and export CSV.
- Watch the live scan feed and current door/controller state.
- Manage people, cards, staff/visitor assignment and card status.
- Edit and publish access schedules and review holidays.
- Inspect device, door, relay, sync and troubleshooting information.
- Onboard additional controllers through the four-step Add Device flow.
- Acknowledge and resolve alerts.
- Use all reports and exports.
- Create Admin and Branch accounts.
- Set which optional pages Admin and Branch can open.
- Hide optional dashboard modules globally for every role.
- See role and scope information, profile, display preferences, integration details and sign out.

**What the Super Admin cannot do**

- Create another Super Admin account from the UI (the form only offers Admin and Branch).
- Edit station records; they are shown as read-only.
- Remotely unlock a door; no remote unlock action is exposed.
- Hide core pages or Users & Roles.
- Make People & Cards, Access Schedules or Add Device available to Branch.

**Default content:** all 12 pages. Hiding optional modules can reduce this to the 6 always-visible pages.

---

### 6.2 Admin

**Workspace:** Area A · area monitoring.

**Default sidebar**

- **Operations:** Overview, Live Monitoring, Access Logs
- **Network:** Stations
- **People & access:** People & Cards, Access Schedules
- **Station:** Device & Door, Add Device, Alerts & Events
- **Insights:** Reports, Settings

**What the Admin can do**

- Monitor the 4 Area A stations: PumpStation 01–04.
- See Area A Overview KPIs, charts, map and recent activity.
- Review logs for the area's station data, filter and export CSV.
- Watch live scans and door/controller state.
- Manage people and cards for the station: add people, assign Staff/Visitor, block/deactivate/activate cards.
- Edit schedules, preview access windows and publish (demo sync).
- Inspect device, door, relay, sync and troubleshooting details.
- Add and register controllers.
- Acknowledge and resolve alerts.
- Use reports and CSV export.
- Change their own password, display preferences and sign out.

**What the Admin cannot do**

- Open Users & Roles.
- Create Admin or Branch accounts.
- Change page permissions.
- Customize or hide dashboard modules.
- See Area B or stations outside Area A.
- Grant themselves pages the Super Admin has denied.
- See People & Cards, Access Schedules or Add Device if the Super Admin removes them.
- Edit station records or remotely unlock a door.

**Default content:** 11 pages. The Super Admin may remove any of the six optional pages.

---

### 6.3 Branch

**Workspace:** Branch 04 · station monitoring.

**Default sidebar**

- **Operations:** Overview, Live Monitoring, Access Logs
- **Network:** Stations
- **Station:** Device & Door, Alerts & Events
- **Insights:** Reports, Settings

**What the Branch can do**

- Monitor the 3 Branch 04 stations: PumpStation 01, 02 and 04.
- See Branch Overview KPIs, charts, map and recent activity.
- Review access logs for the branch scope, filter and export CSV.
- Watch live scans and door/controller state.
- Inspect device, door, relay, sync and troubleshooting details.
- Acknowledge and resolve alerts.
- Use reports and CSV export.
- Change their own password, display preferences and sign out.

**What the Branch cannot do**

- Open Users & Roles.
- Open People & Cards, Access Schedules or Add Device — these pages are not available to the Branch role at all.
- Create or delete accounts.
- Change page permissions.
- Customize or hide dashboard modules.
- See stations outside Branch 04, including Area A stations in Branch 05 or Area B.
- Edit station records or remotely unlock a door.
- Grant themselves a page the Super Admin has denied or hidden.

**Default content:** 8 pages. Live Monitoring, Alerts & Events and Reports are optional and can be removed by the Super Admin; the five core pages and Settings remain.

**Branch scope today:** monitoring is the focus. People/card administration, schedule editing and controller onboarding are intentionally left to Admin and Super Admin.

---

## 7. Permissions and customization

### 7.1 Two separate controls

| Control | Where | Who can change it | Scope |
| --- | --- | --- | --- |
| Page permissions | Users & Roles → Page permissions | Super Admin | Per role (Admin / Branch) |
| Module visibility | Settings → Dashboard customization | Super Admin | Global, every role |

### 7.2 Core vs optional pages

**Core — always available**

- `/overview`
- `/stations`
- `/logs`
- `/device`
- `/settings`
- `/users` (Super Admin only)

**Optional — permission-controlled and hideable**

- `/live`
- `/people`
- `/schedules`
- `/add-device`
- `/alerts`
- `/reports`

### 7.3 Default permissions

| Role | Optional pages on by default |
| --- | --- |
| Admin | Live Monitoring, People & Cards, Access Schedules, Add Device, Alerts & Events, Reports |
| Branch | Live Monitoring, Alerts & Events, Reports |

### 7.4 Enforcement

- **Sidebar:** `navForRole` filters by role, hidden modules and permissions.
- **Route guard:** `canAccessPath` checks the current URL; disallowed routes redirect to `/overview`.
- **Direct URLs:** a denied or hidden page cannot be reached by typing the address.
- **Super Admin:** bypasses page permissions but not hidden modules.
- **Persistence:** role, hidden modules, permissions and user are stored in cookies for 7 days.

### 7.5 Where permissions are stored

| Cookie | Content |
| --- | --- |
| `washroom_role` | `superadmin`, `admin` or `branch` |
| `washroom_hidden` | URL-encoded comma-separated hidden routes |
| `washroom_permissions` | URL-encoded JSON `{ "admin": [...], "branch": [...] }` |
| `washroom_user` | URL-encoded JSON `{ "name": "...", "email": "..." }` |

Managed accounts are stored in `localStorage["washroom_accounts"]`.

---

## 8. Content and mock-data inventory

| Data | Amount / content |
| --- | --- |
| Network stations | 6 across Area A/B and Branch 04/05/07 |
| Station in focus | PumpStation 04, ST-04, Sheikh Zayed Rd · Branch 04 |
| Controller | Dahua DHI-ASI1201E, serial `6H08A84PAJ00107`, firmware `NetSDK 3.060.R.251201` |
| Connection | Ethernet / TCP-IP, IP `10.20.4.11` |
| Door | Washroom Entry · Reader 1, relay `Energised (locked)`, contact `Closed` |
| Map access points | 3: washroom entry, washroom exit, shop staff door |
| People | 8 records, Staff and Visitor roles |
| Cards | 8: 6 active, 1 expired, 1 blocked, MIFARE 13.56 MHz |
| Schedules | 5: staff, VIP, guest, patrol, cleaning |
| Holidays | 3: Commemoration Day, National Day, New Year |
| Alerts | 5: door timeout, blocked card, tamper, controller offline, intrusion |
| Device events | 5: heartbeat, config sync, offline, online, restart |
| Access events | 60 days of deterministic mock events, ~45–70/day, ~13% denied |
| Denial reasons | Invalid card, Expired card, No permission, Outside time section, Card blocked |

---

## 9. What is real and what is demo

**Connected to the real backend**

- Header controller status: REST snapshot + WebSocket updates.
- Add Device: interface discovery, device discovery, initialization, registration, duplicate-update path, re-discovery retry.
- Backend at `http://127.0.0.1:8000`; socket at `ws://127.0.0.1:8000/ws/devices`.

**Mock / local-only**

- Overview KPIs, charts, station map and recent activity.
- Live Monitoring feed.
- Access Logs.
- Stations list and statuses.
- People & Cards edits.
- Access Schedules edits and publish.
- Device & Door page controller state.
- Alerts acknowledge/resolve.
- Reports.
- Settings display preferences and password update.
- Role selection, managed accounts and page permissions.
- Module visibility.

**Known limits**

- Role auth is a demo cookie, not a real session; do not treat it as security.
- Accounts and passwords are stored in `localStorage` in plain text.
- Permissions are stored in a client-readable cookie.
- The demo password fallback still works for emails not in the account list; deleting an account does not fully revoke that fallback login.
- Permissions apply per role, not per account.
- Hiding a module in Settings applies globally to every role.
- The Overview map uses a keyless Google embed; markers do not follow pan/zoom.
- Page-level controller status still comes from mock data; only the header is realtime.
- People, schedules and alert actions are not pushed to the controller yet.

---

## 10. Quick preview checklist

1. Sign in as **Super Admin** with any unused email and the password `super admin`.
2. Confirm all 12 pages are in the sidebar and the workspace says **FuelCo Network**.
3. Open **Stations** — expect 6 stations, 4 online, 1 offline, 1 pending, 15 devices.
4. Open **Users & Roles** — create an Admin account and a Branch account.
5. In **Page permissions**, turn off a page for Admin, save, then sign in as that Admin and confirm the page disappears and its direct URL redirects to `/overview`.
6. Sign in as **S. Khan** / `s.khan@fuelco.example` / `admin` — expect Area A, 4 stations, 11 pages, no Users & Roles.
7. Sign in as **M. Ali** / `m.ali@fuelco.example` / `branch` — expect Branch 04, 3 stations, 8 pages, no People & Cards, Access Schedules, Add Device or Users & Roles.
8. As Super Admin, open **Settings → Dashboard customization**, hide **Reports**, and confirm it disappears for every role.
9. As Super Admin or Admin, open **Add Device** and walk the four steps against the local backend.
10. Confirm the header status badge goes online/offline with the real controller and updates over the WebSocket without polling.
