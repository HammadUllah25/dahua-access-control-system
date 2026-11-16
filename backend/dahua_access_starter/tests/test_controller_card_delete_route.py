"""The retired legacy controller-card REST routes must remain unmounted."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP_DIR = tempfile.TemporaryDirectory(prefix="dahua-retired-routes-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(Path(TEMP_DIR.name) / 'test.db').as_posix()}")
os.environ.setdefault("DEVICE_MONITOR_INTERVAL_SECONDS", "600")
os.environ.setdefault("DEVICE_MONITOR_MAX_WORKERS", "1")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_legacy_controller_card_routes_are_not_public():
    with TestClient(app) as client:
        response = client.get("/devices/1/cards/device-records")
        assert response.status_code == 404, response.text
