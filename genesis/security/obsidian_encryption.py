"""
Obsidian Vault + Chroma Encryption Wrapper
Protects all long-term memory files at rest using Fernet encryption.
"""

from pathlib import Path
import json
from ..security.encryption import secure_storage
from ..config import STORAGE_DIR

VAULT_DIR = STORAGE_DIR / "obsidian_vault"
VAULT_DIR.mkdir(parents=True, exist_ok=True)

def save_encrypted_vault_file(filename: str, content: str | dict) -> str:
    """Encrypt and save file to Obsidian vault."""
    path = VAULT_DIR / filename
    if isinstance(content, dict):
        content = json.dumps(content, indent=2, ensure_ascii=False)
    secure_storage.save_encrypted(path, content)
    return f"✅ Encrypted vault file saved: {filename}"

def load_encrypted_vault_file(filename: str) -> str | dict:
    """Load and decrypt vault file."""
    path = VAULT_DIR / filename
    if not path.exists():
        return ""
    try:
        return secure_storage.load_encrypted(path)
    except:
        return ""

def encrypt_chroma_metadata(metadata: dict) -> bytes:
    """Encrypt Chroma collection metadata."""
    return secure_storage.encrypt(metadata)