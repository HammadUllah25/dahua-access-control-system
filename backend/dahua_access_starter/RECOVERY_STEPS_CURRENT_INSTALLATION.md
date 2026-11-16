# Recovery steps for the current PSO Nooriabad installation

This guide is for the installation with Station ID `1`, Device ID `1`, and the existing legacy card record `FB66983B`.

## 1. Apply the source update without replacing the database or encryption key

1. Stop the running API (`run.bat` console: press `Ctrl+C`).
2. Back up these two existing files somewhere safe:
   - `data/dahua_access.db`
   - `data/device_secret.key`
3. Extract the updated ZIP to a temporary folder.
4. Copy the updated `app` folder and the updated root documentation/test files into your current project folder, allowing source files to be replaced.
5. **Do not overwrite or delete** your existing `.venv`, `.env`, `data/dahua_access.db`, or `data/device_secret.key`.
6. Run `run.bat` again and open `http://127.0.0.1:8000/docs`.

The updated ZIP deliberately excludes `.venv`, the live SQLite database, `.env`, and the device encryption key. This prevents the project update from replacing your existing data or breaking decryption of your saved Dahua password.

## 2. Adopt the already-registered customer card into Station 1

In Swagger, find `POST /stations/{station_id}/cards/adopt-existing` and use `station_id=1` with this body:

```json
{
  "device_id": 1,
  "card_number": "FB66983B",
  "role": "USER",
  "card_name": "Customer Card 01",
  "is_billable": true
}
```

This copies the existing cloud card settings into a station-role assignment. It does not add another card to the hardware and does not delete Person ID 1 or either legacy card row.

The uploaded database also contains a card value `0B56` with the placeholder-style name `string`. **Do not adopt or restore `0B56` as STAFF unless you confirm it is a separate physical RFID card you actually intend to use.** If it is a real staff card, adopt it before the restoration using:

```json
{
  "device_id": 1,
  "card_number": "0B56",
  "role": "STAFF",
  "card_name": "Staff Card 01",
  "is_billable": false
}
```

## 3. Restore the adopted station cards to the controller

You have reported that SmartPSS shows no user/card records after the factory reset. After checking that Device ID 1 is online and the controller is still empty, call `POST /devices/{device_id}/reprovision` with `device_id=1`:

```json
{
  "confirmation": "REPROVISION_FROM_CLOUD",
  "controller_confirmed_factory_reset": true
}
```

This is an explicit one-time restore action. Do not repeat it after it starts. On this ASI1201E installation, the SDK inventory `FindRecord` operation has previously returned an unsupported-operation error. If card insertion succeeds but readback fails, the API returns `verification_required` rather than falsely claiming synchronization. Repeating the restore could create duplicates on firmware where inventory cannot be read, so the API blocks a second confirmed attempt.

## 4. Verify the result

If the response is `verification_required`:

1. Open SmartPSS/device card management and confirm that every adopted card appears.
2. Physically scan each card and confirm it grants access and the lock unlocks.
3. Only after **every** adopted card has passed both checks, call `POST /devices/{device_id}/reprovision/manual-verification`:

```json
{
  "confirmation": "I_VERIFIED_EACH_CARD_IN_SMARTPSS_AND_TESTED_ACCESS",
  "verified_card_numbers": ["FB66983B"]
}
```

The list must exactly match the station assignments for Device ID 1. Include `0B56` only if you adopted and physically verified it too. This records an administrator's manual check; it does not make the unsupported SDK inventory function work.

If the reprovision API reports a card insertion failure, do not repeatedly retry. Preserve the response body and device logs so the specific SDK failure can be diagnosed first.
