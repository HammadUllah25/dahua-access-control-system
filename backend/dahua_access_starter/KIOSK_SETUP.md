# Customer Payment Kiosk (Safepay + Dahua)

This incremental patch adds a same-origin customer kiosk page to the existing FastAPI/Safepay integration. It does not put `REMOTE_UNLOCK_API_KEY` in browser code.

## 1. Apply the patch

Extract `dahua_safepay_kiosk_patch.zip` into the existing `dahua_access_starter` project and allow the included files to replace their matching paths. Do not replace your real `.env`, database file, or `data/device_secret.key`.

## 2. Configure the kiosk in your existing `.env`

Keep your Safepay credentials and existing Dahua settings. Add:

```env
# Customer-facing kiosk
KIOSK_PUBLIC_ENABLED=true
KIOSK_STATION_ID=1
KIOSK_DEVICE_ID=1
KIOSK_DOOR_INDEX=0
KIOSK_ALLOWED_NETWORKS=127.0.0.1/32,::1/128
```

- `KIOSK_STATION_ID=1` is the configured station.
- `KIOSK_DEVICE_ID=1` is the Dahua controller. Leave it blank only if the station has exactly one controller.
- `KIOSK_DOOR_INDEX=0` is the door index.
- The default network list allows the kiosk on the same Windows machine. If the kiosk browser runs on another device, add only that trusted LAN subnet, for example `192.168.0.0/24`. Do not allow the whole internet.
- `PAYMENT_ENTRY_FEE_MINOR=100` means PKR 1.00. The displayed price comes from this backend setting.

The public kiosk endpoint can create payments only for the configured station/controller/door. It cannot call the Dahua unlock API directly. The master `REMOTE_UNLOCK_API_KEY` remains server-side and is still required for the sandbox simulator and administrative operations.

## 3. Start and open the kiosk

Start the backend using the existing project command:

```powershell
.\run.bat
```

Open this address on the same Windows computer:

```text
http://127.0.0.1:8000/kiosk/1
```

For a full-screen Microsoft Edge kiosk window:

```powershell
Start-Process msedge.exe '--kiosk http://127.0.0.1:8000/kiosk/1 --edge-kiosk-type=fullscreen'
```

## 4. Customer flow

1. Customer taps **Pay & continue**.
2. The kiosk calls `POST /stations/1/payments/raast-qr` without exposing the admin key.
3. FastAPI creates the fixed-amount Safepay tracker and displays the returned QR image.
4. The kiosk checks `GET /payments/{payment_id}/status` every three seconds using the per-payment status token.
5. Only a provider-verified captured/settled payment can trigger `sessions.open_door()`.
6. The kiosk displays success only after the backend records `COMMAND_ACCEPTED`. That is controller command acknowledgement, not physical door-position verification.

The payment ID, status token and QR are retained in the browser tab's `sessionStorage` so the page can resume polling after a reload in the same tab. The status token is never written to server logs by this page.

## 5. Sandbox limitation and physical unlock test

Safepay's sandbox Raast QR is simulated and cannot be paid using a real banking app. For a controlled physical-door test:

1. Set `SAFEPAY_ENABLE_TEST_SIMULATOR=true` in `.env` and restart the backend.
2. Open the kiosk and create a payment QR.
3. In Swagger, call `POST /payments/{payment_id}/sandbox-simulate-capture` for that kiosk payment.
4. Supply the existing `X-Unlock-API-Key` header in Swagger. Never put this key in the kiosk browser.
5. The kiosk should detect `PAID_TEST` and show the sandbox-test success screen after the actual Dahua command is accepted.
6. Set `SAFEPAY_ENABLE_TEST_SIMULATOR=false` and restart the backend immediately after testing.

This sends a real remote-open command to the configured Dahua door, but it does not collect real money. Keep the area safe during the test.

## 6. Network and deployment notes

- `run.bat` binds Uvicorn to `127.0.0.1`, which is correct for a kiosk browser running on the same PC.
- If the kiosk is on another device, bind the backend to the LAN interface (for example `0.0.0.0`), add the kiosk subnet to `KIOSK_ALLOWED_NETWORKS`, and create a Windows Firewall rule restricted to that private subnet. Do not expose the public kiosk endpoint to the internet.
- The current network allowlist and five-second QR-create cooldown are process-local protections for a single kiosk. A multi-worker/public production deployment should use shared rate limiting and a stronger kiosk-device authentication mechanism.
- Sandbox mode cannot validate a real bank scan. Real scan-and-pay requires Safepay to enable live Raast for the merchant and production credentials.
