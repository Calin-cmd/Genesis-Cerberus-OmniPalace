"""
Genesis Security - Encryption Layer
Handles at-rest encryption for all persistent data using Fernet + keyring.
"""

from __future__ import annotations
import os
from pathlib import Path
from cryptography.fernet import Fernet
import keyring
import json

from ..config import STORAGE_DIR

class EncryptedStorage:
    """Secure encrypted storage wrapper for memory, Chroma metadata, and traces."""

    KEY_NAME = "genesis_master_key"
    KEY_FILE = STORAGE_DIR / ".master.key"

    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)

    def _get_or_create_key(self) -> bytes:
        """Get key from OS keyring or generate new one."""
        key = keyring.get_password("genesis", self.KEY_NAME)
        if key:
            return key.encode()

        # Generate new key on first run
        key = Fernet.generate_key()
        keyring.set_password("genesis", self.KEY_NAME, key.decode())

        # Backup to file (with warning)
        self.KEY_FILE.write_bytes(key)
        print("⚠️  New encryption key generated and stored in OS keyring.")
        return key

    def encrypt(self, data: dict | str | bytes) -> bytes:
        """Encrypt data to bytes."""
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        if isinstance(data, str):
            data = data.encode("utf-8")
        return self.cipher.encrypt(data)

    def decrypt(self, encrypted_data: bytes) -> dict | str:
        """Decrypt bytes back to original data."""
        decrypted = self.cipher.decrypt(encrypted_data)
        try:
            return json.loads(decrypted)
        except:
            return decrypted.decode("utf-8")

    def save_encrypted(self, filepath: Path, data: dict):
        """Save encrypted data to file."""
        encrypted = self.encrypt(data)
        filepath.write_bytes(encrypted)

    def load_encrypted(self, filepath: Path) -> dict:
        """Load and decrypt data from file."""
        if not filepath.exists():
            return {}
        encrypted = filepath.read_bytes()
        return self.decrypt(encrypted)


# Global instance
secure_storage = EncryptedStorage()