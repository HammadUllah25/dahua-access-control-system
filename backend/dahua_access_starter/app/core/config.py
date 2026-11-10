from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).resolve()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'dahua_access.db'}")
APP_NAME = os.getenv("APP_NAME", "Dahua Access Control API")
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
