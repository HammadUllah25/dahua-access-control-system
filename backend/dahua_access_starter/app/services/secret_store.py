from __future__ import annotations

from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import DATA_DIR


_KEY_PATH = DATA_DIR / "device_secret.key"


def _fernet() -> Fernet:
    """Load or create the local development encryption key.

    IMPORTANT: Back up device_secret.key securely. If it is lost, saved device
    passwords cannot be decrypted and must be entered again.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _KEY_PATH.exists():
        key = Fernet.generate_key()
        _KEY_PATH.write_bytes(key)
        try:
            _KEY_PATH.chmod(0o600)
        except OSError:
            pass  # Windows does not implement POSIX permission bits.
    return Fernet(_KEY_PATH.read_bytes())


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Could not decrypt the device password. Check data/device_secret.key.") from exc
