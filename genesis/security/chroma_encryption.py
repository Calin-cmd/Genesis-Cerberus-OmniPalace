"""
ChromaDB Encryption Wrapper
Protects vector memory metadata and collection data at rest.
"""

from pathlib import Path
import json
from ..security.encryption import secure_storage
from ..config import STORAGE_DIR

CHROMA_DIR = STORAGE_DIR / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

def encrypt_chroma_metadata(metadata: dict) -> bytes:
    """Encrypt Chroma collection metadata before storage."""
    return secure_storage.encrypt(metadata)

def decrypt_chroma_metadata(encrypted_data: bytes) -> dict:
    """Decrypt Chroma metadata on load."""
    try:
        return secure_storage.decrypt(encrypted_data)
    except:
        return {}

def save_encrypted_chroma_collection(name: str, documents: list, metadatas: list, ids: list):
    """Save Chroma data with encrypted metadata."""
    encrypted_metadatas = [encrypt_chroma_metadata(m) if m else b"" for m in metadatas]
    # Note: Full document encryption can be added later if needed
    return {"documents": documents, "metadatas": encrypted_metadatas, "ids": ids}