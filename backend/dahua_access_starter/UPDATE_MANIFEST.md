# Update manifest

This build layers the latest user-provided device identity API and the post-archive changes described in the conversation onto the most recent complete backend starter archive available in the conversation.

## Preserved backend features

- Dahua NetSDK initialization and login adapter
- Device registration, connection, disconnection, deletion, health checks, and monitoring
- Serial-number and MAC-address duplicate prevention (private host/IP addresses are not globally unique)
- LAN discovery and first-time device account initialization
- Person records, access-card assignments, device card synchronization/import, and their existing APIs
- Existing SQLite tables and additive migrations for monitoring, import metadata, and device identity

## Added/updated in this build

- Alarm event subscription using `SetDVRMessCallBackEx1` and `StartListenEx`
- `NET_A_ALARM_ACCESS_CTL_EVENT_INFO` parser for card number, user ID, name, reader, door, direction, event time, raw status, and error code
- `bStatus` mapping (`TRUE` = `granted`, `FALSE` = `denied`) per the vendor SDK structure comment
- Background event persistence into SQLite `access_events`
- REST endpoints for access-event history, details, and summary counters
- Shared Ethernet-only IPv4 adapter filtering for both network and device-initialization interface endpoints
- Correct use of `socket.AF_INET` in adapter enumeration
- Safe replacement instructions that protect `.env` and the existing database

## Scope and verification limits

- This is the FastAPI backend starter folder, not the user's entire parent Git repository or a separate frontend/dashboard project.
- Local `.env`, the user's SQLite database, virtual environment, and the Dahua SDK wheel are intentionally excluded.
- Source syntax, SQLite migrations, endpoint behavior, duplicate identity checks, event decoding, event persistence, and summary counts were tested in an offline container.
- A live subscription and physical card-scan test on the user's ASI1201E has not been performed from this build environment.
