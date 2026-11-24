# Safepay Raast QR + Dahua unlock (sandbox patch)

This patch adds a first sandbox integration to the existing FastAPI backend.

## What is implemented

- Fixed entry price configured as `PAYMENT_ENTRY_FEE_MINOR=100` (PKR 1.00).
- Safepay Raast tracker creation and Dynamic QR request.
- Server-side tracker status polling.
- Payment verification against tracker token, amount, currency, `TRACKER_ENDED`, and Raast `CAPTURED`/`SETTLED` state.
- An atomic database claim (`not_started` -> `processing`) before calling the existing Dahua `sessions.open_door()` method. Repeated polls cannot issue a second command for the same payment.
- A payment audit event through the existing `record_remote_unlock_event()` service.
- A sandbox-only simulator to test the door-unlock path because Safepay documents that its sandbox Raast QR is mocked and cannot be paid by a real banking app.

The simulator is NOT a Safepay confirmation and must remain disabled except during a controlled local test.

## 1. Safepay sandbox credentials

In the Safepay sandbox dashboard, open **Developers -> API** and copy:

- Public API key (used as `SAFEPAY_MERCHANT_API_KEY`; Safepay's Raast tracker API calls this `merchant_api_key`).
- Private API Secret key (used as `SAFEPAY_SECRET_KEY`).

The webhook/HMAC secret is not needed for this first polling-based sandbox phase. Do not paste credentials into chat, source files, or Git.

## 2. Add settings to your existing `.env`

Keep all existing Dahua and database settings. Add:

```env
SAFEPAY_ENV=sandbox
SAFEPAY_HOST=https://sandbox.api.getsafepay.com
SAFEPAY_SECRET_KEY=YOUR_SANDBOX_PRIVATE_API_SECRET
SAFEPAY_MERCHANT_API_KEY=YOUR_SANDBOX_PUBLIC_API_KEY
SAFEPAY_TIMEOUT_SECONDS=15

PAYMENT_ENTRY_FEE_MINOR=100
PAYMENT_QR_TTL_MINUTES=5
SAFEPAY_ENABLE_TEST_SIMULATOR=false
```

`100` means PKR 1.00. Safepay uses minor currency units. The requested PKR 1 amount is sent to Safepay; the merchant account/API may still enforce its own amount limits.

For a controlled physical-door test only, set:

```env
SAFEPAY_ENABLE_TEST_SIMULATOR=true
```

This flag is rejected when `SAFEPAY_ENV=production`. Never expose the simulator endpoint publicly, and turn the flag off immediately after testing.

## 3. Apply patch files

Copy the files from this patch into the same relative paths in your existing `dahua_access_starter` project, allowing the replacement versions of `app/core/config.py`, `app/main.py`, and `app/models/__init__.py` to overwrite those files. Merge the added Safepay lines into your real `.env` manually; do not replace the real `.env` with `.env.example`.

No new Python packages are required: this project already lists `requests` and `qrcode[pil]` in `requirements.txt`.

On startup, the existing `Base.metadata.create_all()` creates the new `payment_transactions` table. Existing tables and data are not dropped or rewritten.

## 4. Start backend and confirm routes

Start using your existing command:

```powershell
.\run.bat
```

Open:

```text
http://127.0.0.1:8000/docs
```

Look for the **Safepay Payments** tag and these routes:

- `POST /stations/{station_id}/payments/raast-qr`
- `GET /payments/{payment_id}/status`
- `POST /payments/{payment_id}/sandbox-simulate-capture`

## 5. Create a Safepay sandbox QR

In Swagger, call:

```http
POST /stations/1/payments/raast-qr
```

Header:

```text
X-Unlock-API-Key: YOUR_EXISTING_REMOTE_UNLOCK_API_KEY
```

Body:

```json
{
  "device_id": 1,
  "door_index": 0
}
```

Expected result: pending payment, tracker token, raw EMVCo QR payload, QR image data URL, `payment_id`, and a one-time `status_token`.

Render `qr_image_data_url` on the kiosk. Keep `status_token` private to the kiosk session and do not log it.

## 6. Poll the payment status

Call every 3-5 seconds while the QR is active:

```http
GET /payments/{payment_id}/status
```

Header:

```text
X-Payment-Access-Token: THE_STATUS_TOKEN_FROM_CREATE_RESPONSE
```

The backend checks Safepay. Only a matching tracker, exact stored amount/currency, `TRACKER_ENDED`, and Raast `CAPTURED` or `SETTLED` are accepted as a real provider-confirmed payment. `INITIATED` is pending and never unlocks the door.

## 7. Test the Dahua path in sandbox

Safepay's current Raast documentation says sandbox Raast initiation returns a mock QR that cannot be paid using a banking app. Therefore, you cannot complete a real bank-to-Safepay Raast transaction in sandbox.

To check that a payment record reaches the existing Dahua controller, and only while standing at the controller with the door area safe:

1. Set `SAFEPAY_ENABLE_TEST_SIMULATOR=true` in `.env`.
2. Restart the backend.
3. Create a sandbox QR using step 5.
4. Call:

```http
POST /payments/{payment_id}/sandbox-simulate-capture
```

Header:

```text
X-Unlock-API-Key: YOUR_EXISTING_REMOTE_UNLOCK_API_KEY
```

This labels the transaction `PAID_TEST`, records that the status was locally simulated, and tests the single-claim unlock logic. It does not assert that Safepay received money. It will physically send a remote-open command to the configured Dahua door.
5. Check `GET /access-events?device_id=1&limit=100&offset=0` for the audit event with operator `SAFEPAY_RAAST_TEST` and reason `SANDBOX_PAYMENT_TEST`.
6. Set `SAFEPAY_ENABLE_TEST_SIMULATOR=false` again and restart.

## 8. Important boundaries

- `command_accepted` means the Dahua SDK/controller accepted the remote-open command. It does not independently prove the physical door opened; door sensor verification remains separate.
- Payment status and unlock status are separate. If the payment is captured while the controller is offline, the payment remains paid and the unlock is marked failed; do not charge the customer again.
- The payment status endpoint uses a random per-payment access token. The QR creation and test-simulator endpoints require the existing server-side `REMOTE_UNLOCK_API_KEY`. Never expose that API key in browser JavaScript.
- This initial integration uses server-side status polling. A production deployment should add signed Safepay webhooks and a durable worker/retry process, and should use PostgreSQL/Neon row-level coordination when running multiple backend processes.
- The shared project ZIP does not contain the original SQLite database file or `device_secret.key`. This patch does not touch either file. Keep them backed up.
