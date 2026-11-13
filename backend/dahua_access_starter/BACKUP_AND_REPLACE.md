# Install the ASI1201E card-enrollment update safely

## Before replacing the backend

1. Stop the running Uvicorn process with `Ctrl+C`.
2. Make a backup copy of your current `backend/dahua_access_starter` folder.
3. Preserve these existing local files:
   - `data/dahua_access.db`
   - `data/device_secret.key`
   - `.env` (if you use one)
4. Extract the release ZIP. Copy its `dahua_access_starter` folder into your existing `backend` folder and allow source files to be replaced. Do not delete the existing `data` folder or the two data files above.

The release ZIP deliberately excludes the application database, encryption key, `.env`, and Python virtual environments. A new project-local `.venv` is created during setup so the Dahua wheel and FastAPI run under one interpreter.

## Install dependencies and the bundled Dahua SDK

1. Open the updated `backend/dahua_access_starter` folder.
2. Double-click `install.bat`.
3. Wait for the setup verification to finish with `PASS` messages.
4. Run `python tools\test_card_update_mock.py` from this folder to verify the offline card-update regression test. This does not contact the controller.

`install.bat` creates `.venv`, installs `requirements.txt`, installs the bundled NetSDK 2.0.0.1 Windows x64 wheel from `vendor`, and runs `tools/verify_setup.py`.

## Start the API

Double-click `run.bat`, then open:

`http://127.0.0.1:8000/docs`

The launch script explicitly calls `dahua_access_starter/.venv/Scripts/python.exe`; it does not use the old sibling `backend/venv`.

## Updated scan-to-enroll confirmation

1. Confirm the target person exists in `GET /persons`.
2. Start a fresh `POST /devices/{device_id}/card-enrollments` session.
3. Present a test card and poll the session until `status` is `captured`.
4. Confirm using `POST /devices/{device_id}/card-enrollments/{session_token}/confirm` with `person_id`, `card_name`, `card_type`, `is_valid`, `valid_from`, `valid_until`, `door_indices`, and `time_section_indices`.
5. Verify the result in `GET /devices/{device_id}/cards` and `GET /devices/{device_id}/cards/device-records`.
6. Test the physical door with the test card.

The confirmation endpoint now writes the card record using the existing `CLIENT_ControlDevice` / `RECORDSET_INSERT` path and saves the person-to-card relation in SQLite. It does not call the optional personnel `OperateAccessUserService` GET/INSERT/REMOVE methods, which were the source of the previously observed `0x00000015` failure during confirmation.

## Verification boundary

Offline tests, Python compilation, OpenAPI generation, and SDK structure checks have passed. The native Dahua DLL call and physical ASI1201E firmware behavior must still be verified on the Windows PC connected to the actual controller. Start with a spare card; first check whether its UID already exists on the controller or in the application. In particular, do not treat a successful SDK update response as proof that `is_valid=False` blocks door access until this is confirmed with a spare card and access-event logs.

## Security and database notes

- Do not send or share `data/dahua_access.db` together with `data/device_secret.key`.
- Keep `device_secret.key` backed up securely. If it is lost, saved device passwords cannot be decrypted.
- The API currently binds to `127.0.0.1` and does not provide application authentication. Keep it on a trusted PC/LAN workflow; do not expose it publicly without adding authentication and authorization.
