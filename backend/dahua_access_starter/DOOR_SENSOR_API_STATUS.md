# Door sensor API status (ASI1201E)

## Read API

`GET /devices/{device_id}/door-config` reads the controller's `AccessControl` configuration through the existing Dahua NetSDK login/session (`GetNewDevConfig`). The parser handles the array-shaped `params.table` returned by Dahua as well as firmware responses that expose a single object. The optional `door_index` query parameter is zero-based and defaults to `0`.

The response includes `SensorEnable`, `CloseCheckSensor` (when present), `CloseTimeout`, and `DoorNotClosedAlarmEnable`. Reading configuration does not modify the device.

## Write API

`PUT /devices/{device_id}/door-config` accepts `sensor_enabled` and an optional zero-based `door_index` (default `0`). It reads the current `AccessControl` payload, changes only the selected entry's `SensorEnable` value, and submits the preserved JSON payload through Dahua NetSDK `SetNewDevConfig`. It then reads the configuration again and confirms that `SensorEnable` matches the requested value. A write is not reported as successful unless the read-back matches.

Example body:

```json
{
  "sensor_enabled": true,
  "door_index": 0
}
```

Both endpoints use the device's configured NetSDK port. They do not use the `DAHUA_HTTP_PORT` setting or make a port-80 CGI request.

## Verification

Automated tests cover array- and object-shaped read responses, preservation of unrelated door settings during a write, and read-back verification. Physical write behavior still needs to be confirmed against the target ASI1201E and its installed firmware.
