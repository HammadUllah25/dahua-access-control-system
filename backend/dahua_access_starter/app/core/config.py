from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).resolve()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'dahua_access.db'}")
APP_NAME = os.getenv("APP_NAME", "Dahua Access Control API")
PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "").strip().rstrip("/")
QR_ACCESS_TTL_SECONDS = 60
DEVICE_ENCRYPTION_KEY = os.getenv("DEVICE_ENCRYPTION_KEY", "").strip() or None
SDK_LOG_DIR = Path(os.getenv("SDK_LOG_DIR", str(DATA_DIR / "sdk_logs"))).resolve()
SDK_CONNECT_TIMEOUT_MS = int(os.getenv("SDK_CONNECT_TIMEOUT_MS", "5000"))
SDK_CONNECT_RETRY = int(os.getenv("SDK_CONNECT_RETRY", "1"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
SDK_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Device monitoring defaults. Configure through environment variables for testing.
DEVICE_MONITOR_INTERVAL_SECONDS = float(os.getenv("DEVICE_MONITOR_INTERVAL_SECONDS", "10"))
DEVICE_MONITOR_TCP_TIMEOUT_SECONDS = float(os.getenv("DEVICE_MONITOR_TCP_TIMEOUT_SECONDS", "1.5"))
DEVICE_MONITOR_FAILURE_THRESHOLD = int(os.getenv("DEVICE_MONITOR_FAILURE_THRESHOLD", "2"))
DEVICE_MONITOR_RECONNECT_COOLDOWN_SECONDS = float(
    os.getenv("DEVICE_MONITOR_RECONNECT_COOLDOWN_SECONDS", "30")
)
DEVICE_MONITOR_MAX_WORKERS = int(os.getenv("DEVICE_MONITOR_MAX_WORKERS", "32"))

# Safepay payment integration (sandbox by default). Never commit real credentials.
SAFEPAY_ENV = os.getenv("SAFEPAY_ENV", "sandbox").strip().lower()
SAFEPAY_HOST = os.getenv(
    "SAFEPAY_HOST",
    "https://sandbox.api.getsafepay.com" if SAFEPAY_ENV == "sandbox" else "https://api.getsafepay.com",
).strip().rstrip("/")
SAFEPAY_SECRET_KEY = os.getenv("SAFEPAY_SECRET_KEY", "").strip()
SAFEPAY_MERCHANT_API_KEY = os.getenv("SAFEPAY_MERCHANT_API_KEY", "").strip()
SAFEPAY_TIMEOUT_SECONDS = float(os.getenv("SAFEPAY_TIMEOUT_SECONDS", "15"))
PAYMENT_ENTRY_FEE_MINOR = int(os.getenv("PAYMENT_ENTRY_FEE_MINOR", "100"))
PAYMENT_QR_TTL_MINUTES = int(os.getenv("PAYMENT_QR_TTL_MINUTES", "5"))
SAFEPAY_ENABLE_TEST_SIMULATOR = os.getenv("SAFEPAY_ENABLE_TEST_SIMULATOR", "false").strip().lower() in {"1", "true", "yes"}
KIOSK_LOCAL_SIMULATOR_ENABLED = os.getenv("KIOSK_LOCAL_SIMULATOR_ENABLED", "false").strip().lower() in {"1", "true", "yes"}

# Public kiosk settings. The kiosk browser never receives REMOTE_UNLOCK_API_KEY.
KIOSK_PUBLIC_ENABLED = os.getenv("KIOSK_PUBLIC_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
KIOSK_STATION_ID = int(os.getenv("KIOSK_STATION_ID", "1"))
KIOSK_DEVICE_ID_RAW = os.getenv("KIOSK_DEVICE_ID", "").strip()
KIOSK_DEVICE_ID = int(KIOSK_DEVICE_ID_RAW) if KIOSK_DEVICE_ID_RAW else None
KIOSK_DOOR_INDEX = int(os.getenv("KIOSK_DOOR_INDEX", "0"))
KIOSK_ALLOWED_NETWORKS = tuple(
    item.strip()
    for item in os.getenv("KIOSK_ALLOWED_NETWORKS", "127.0.0.1/32,::1/128").split(",")
    if item.strip()
)
if SAFEPAY_ENV not in {"sandbox", "production"}:
    raise ValueError("SAFEPAY_ENV must be 'sandbox' or 'production'.")
if not 1 <= PAYMENT_QR_TTL_MINUTES <= 180:
    raise ValueError("PAYMENT_QR_TTL_MINUTES must be between 1 and 180.")
if PAYMENT_ENTRY_FEE_MINOR <= 0:
    raise ValueError("PAYMENT_ENTRY_FEE_MINOR must be greater than zero.")
if SAFEPAY_ENV == "production" and (SAFEPAY_ENABLE_TEST_SIMULATOR or KIOSK_LOCAL_SIMULATOR_ENABLED):
    raise ValueError("Payment simulators cannot be enabled in production.")
