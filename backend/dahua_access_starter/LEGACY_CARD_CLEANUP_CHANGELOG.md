# Change log — legacy card cleanup

- Added `DELETE /devices/{device_id}/cards/{assignment_id}/legacy-assignment`.
- The new route removes only a person-linked `AccessCard` database record.
- It performs no device connection, SDK request, or physical card deletion.
- A station-role assignment is stored in a separate table and is not modified.
- Verified against the uploaded database: deleting legacy assignment ID 2 (`0B56`) leaves station-card assignment ID 1 (`FB66983B`, `USER`) intact; deleting Person ID 1 succeeds afterwards.
