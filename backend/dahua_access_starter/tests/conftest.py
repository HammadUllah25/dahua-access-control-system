"""Every pytest run uses a throwaway SQLite database, never data/dahua_access.db.

Loaded by pytest before any test module, so it wins over the per-file setdefault() calls
and over a test file that imports the app first.
"""
import os
import tempfile
from pathlib import Path

_TEMP_DIR = tempfile.TemporaryDirectory(prefix="dahua-pytest-", ignore_cleanup_errors=True)
TEST_DATABASE_URL = f"sqlite:///{(Path(_TEMP_DIR.name) / 'test.db').as_posix()}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("DEVICE_MONITOR_INTERVAL_SECONDS", "600")
os.environ.setdefault("DEVICE_MONITOR_MAX_WORKERS", "1")
