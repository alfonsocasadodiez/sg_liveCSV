"""Encryption helpers for secrets stored on disk (e.g. the ShotGrid script key)."""
import os
import stat

from cryptography.fernet import Fernet, InvalidToken

ENC_PREFIX = "enc:"


def _load_or_create_key(key_path: str) -> bytes:
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read().strip()

    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(key_path) or ".", exist_ok=True)
    with open(key_path, "wb") as f:
        f.write(key)
    os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    return key


class SecretBox:
    """Encrypts/decrypts secret strings using a key kept on disk, separate from config."""

    def __init__(self, key_path: str):
        self.key_path = key_path
        self._fernet = Fernet(_load_or_create_key(key_path))

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        token = self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
        return ENC_PREFIX + token

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        if not value.startswith(ENC_PREFIX):
            # Not encrypted (e.g. plaintext migrated from an older config); return as-is.
            return value
        token = value[len(ENC_PREFIX):]
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken:
            return ""

    @staticmethod
    def is_encrypted(value: str) -> bool:
        return bool(value) and value.startswith(ENC_PREFIX)
