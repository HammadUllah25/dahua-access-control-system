# Legacy card assignment cleanup (database only)

This update adds a safe endpoint for removing an obsolete person-linked card row without sending a delete command to the Dahua controller.

## Apply the update

1. Stop the FastAPI server.
2. Back up your current `data/dahua_access.db` and `data/device_secret.key` together.
3. Extract this ZIP to a temporary folder.
4. Copy the updated `app` folder into your existing project and allow it to overwrite files.
5. Do **not** replace your existing `data` folder, `.env`, `.venv`, or device secret key.
6. Start the backend again using your normal `run.bat`.

## Delete the obsolete legacy assignment

Open `http://127.0.0.1:8000/docs` and execute:

```http
DELETE /devices/1/cards/2/legacy-assignment
```

This endpoint:

- deletes only the `AccessCard` legacy database row with `id=2` and `device_id=1`;
- does not connect to the controller;
- does not call the Dahua SDK;
- does not delete or modify a `StationCardAssignment`;
- returns `controller_modified: false` in its response.

For the database included with the project at packaging time, assignment ID 2 is card `0B56`, linked to Person ID 1. The active station assignment is a separate row: station-card assignment ID 1, card `FB66983B`, role `USER`. That station assignment is not targeted by this endpoint.

Example successful response:

```json
{
  "deleted": true,
  "deletion_type": "legacy_database_only",
  "assignment_id": 2,
  "person_id": 1,
  "device_id": 1,
  "card_number": "0B56",
  "controller_modified": false,
  "station_assignment_preserved": false,
  "station_assignment_id": null,
  "note": "Only the legacy person-linked database assignment was deleted. No Dahua command was sent."
}
```

The `station_assignment_preserved` value is `false` in this example because `0B56` is not the station card `FB66983B`. The station assignment table is not modified in either case.

## Then remove the old person

After confirming that `GET /devices/1/cards` no longer lists any legacy assignments for Person ID 1, execute:

```http
DELETE /persons/1
```

It should now succeed because the person no longer has legacy `AccessCard` assignments.

## Verify the working station card remains

Execute:

```http
GET /stations/1/cards
```

Confirm that `FB66983B` is still present with role `USER` and `is_billable: true`.

Do not use the existing `DELETE /devices/1/cards/2` endpoint for this cleanup. That endpoint attempts a physical Dahua card deletion and is not suitable for removing a stale legacy database-only record.
