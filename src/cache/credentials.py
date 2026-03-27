"""Encrypted S3 credential storage for jrvltsql cache sync.

Credentials are encrypted with AES-256-GCM using a master password.
Key is derived via PBKDF2-HMAC-SHA256 (100k iterations).

File format (config/s3_credentials.enc):
  [16 bytes salt][12 bytes nonce][variable: GCM ciphertext+tag]
"""

import json
import os
import struct
from pathlib import Path
from typing import Optional

DEFAULT_CRED_PATH = Path("config/s3_credentials.enc")
_SALT_LEN = 16
_NONCE_LEN = 12
_KEY_LEN = 32  # AES-256
_ITERATIONS = 100_000


def _derive_key(password: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_credentials(data: dict, password: str) -> bytes:
    """Encrypt credential dict with password → raw bytes."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(password, salt)
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return salt + nonce + ciphertext


def decrypt_credentials(raw: bytes, password: str) -> dict:
    """Decrypt raw bytes with password → credential dict.

    Raises:
        ValueError: If password is wrong or data is corrupted.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag
    if len(raw) < _SALT_LEN + _NONCE_LEN + 1:
        raise ValueError("Credential file is too short or corrupted")
    salt = raw[:_SALT_LEN]
    nonce = raw[_SALT_LEN:_SALT_LEN + _NONCE_LEN]
    ciphertext = raw[_SALT_LEN + _NONCE_LEN:]
    key = _derive_key(password, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except InvalidTag:
        raise ValueError("Wrong password or corrupted credential file")
    return json.loads(plaintext.decode("utf-8"))


class CredentialManager:
    """Manages encrypted S3 credentials.

    Example::

        mgr = CredentialManager()
        mgr.save({"endpoint_url": "...", "aws_access_key_id": "...",
                  "aws_secret_access_key": "...", "bucket_name": "..."}, password="secret")
        creds = mgr.load(password="secret")
    """

    def __init__(self, path: Path = DEFAULT_CRED_PATH):
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def save(self, credentials: dict, password: str) -> None:
        """Encrypt and save credentials to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = encrypt_credentials(credentials, password)
        self.path.write_bytes(raw)

    def load(self, password: str) -> dict:
        """Load and decrypt credentials from disk.

        Raises:
            FileNotFoundError: If credentials file does not exist.
            ValueError: If password is wrong.
        """
        if not self.path.exists():
            raise FileNotFoundError(
                f"S3 credentials not found: {self.path}\n"
                "Run: jltsql cache s3-setup"
            )
        raw = self.path.read_bytes()
        return decrypt_credentials(raw, password)

    def delete(self) -> None:
        """Delete credentials file."""
        if self.path.exists():
            self.path.unlink()
