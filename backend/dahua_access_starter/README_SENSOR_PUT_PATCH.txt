Dahua ASI1201E sensor PUT patch
================================

This patch changes only the AccessControl door-sensor write path and its tests.
It does not replace your .venv, NetSDK DLLs, database, environment files, or any
other backend files.

Files in this archive (extract into the backend project root):
  app/services/dahua_access_control_structs.py  [new]
  app/services/dahua_sdk.py                     [updated]
  app/services/door_config.py                   [updated]
  tests/test_door_sensor_config.py              [updated]

Implementation:
  - Reads the current AccessControl JSON from the device.
  - Uses CLIENT_ParseData to convert it to CFG_ACCESS_EVENT_INFO.
  - Changes only the sensor flags according to Dahua's AccessControl demo.
  - Uses CLIENT_PacketData and CLIENT_SetNewDevConfig.
  - Checks the SDK function result and detailed configuration status.
  - Reads the setting back from the controller before returning success.

Safety and compatibility notes:
  - This archive does not contain Dahua's C header files. The ctypes layout is
    based on the published NetSDK structure layout and is guarded by a strict
    CLIENT_ParseData output-size check plus comparisons of several parsed
    fields against the device's JSON response. This is not a substitute for
    compiling against the exact V3.060 C header or testing the physical device.
  - No physical ASI1201E write was performed while preparing this patch.
  - Do not treat a passing unit test as proof that the controller accepted a
    hardware write. The endpoint performs a read-back check and only reports
    success when the controller reports the requested SensorEnable value.
  - If the runtime parser size or cross-check fields do not match, the code
    refuses to call CLIENT_SetNewDevConfig.

Apply:
  1. Back up your current backend folder or commit your current work.
  2. Extract this archive into the backend project root and allow the four
     listed files to be replaced/added.
  3. Do not replace or delete your .venv or Dahua runtime DLLs.
  4. Run: python -m pytest -q
  5. Restart the FastAPI backend.
  6. First GET the current door config. Then perform one controlled PUT test
     with the sensor physically connected, and GET again to confirm read-back.

Expected API body for enabling sensor (door 0):
  {"sensor_enabled": true, "door_index": 0}

The GET endpoint remains available at:
  GET /devices/{device_id}/door-config?door_index=0

The PUT endpoint remains available at:
  PUT /devices/{device_id}/door-config
