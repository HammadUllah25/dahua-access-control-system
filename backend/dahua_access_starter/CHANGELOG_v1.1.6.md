# v1.1.6 — Door Sensor Configuration

## Added
- `GET /devices/{device_id}/door-config` reads the controller's `AccessControl[n].SensorEnable` setting.
- `PUT /devices/{device_id}/door-config` updates only the selected door sensor flag.
- The PUT operation requires a successful controller readback before returning `verified: true`.
- Dahua CGI access uses HTTP Digest authentication with the stored encrypted device password.
- HTTP configuration port defaults to 80 and is configurable through `DAHUA_HTTP_PORT`.

## Important
- ASI1201E single-door controller uses `door_index: 0`.
- The implementation uses Dahua's documented `configManager.cgi` AccessControl configuration interface.
- Offline tests passed; a physical ASI1201E read/write/readback test is still required.
- If the controller uses a non-default HTTP port, set `DAHUA_HTTP_PORT` in `.env`.
