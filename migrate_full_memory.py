"""
One-time full memory migration to encrypted storage.
Run once, then delete.
"""

import sys
from pathlib import Path
import shutil
import json
from datetime import datetime

sys.path.insert(0, ".")

from genesis.config import STORAGE_DIR, STORAGE_PATH
from genesis.security.encryption import secure_storage
from genesis.agent_memory.core import AgentMemory

print("🔐 Starting full memory migration to encrypted storage...")

backup_dir = STORAGE_DIR / "backup_pre_full_encryption"
backup_dir.mkdir(exist_ok=True)

# Backup everything
if STORAGE_PATH.exists():
    shutil.copy(STORAGE_PATH, backup_dir / "memory.json")
print(f"✅ Backed up old memory to {backup_dir}")

# Load old unencrypted data if it exists
old_data = {}
if STORAGE_PATH.exists():
    try:
        old_data = json.loads(STORAGE_PATH.read_text(encoding="utf-8"))
        print(f"✅ Loaded old data with {len(old_data.get('sessions', {}))} sessions")
    except:
        print("⚠️ Could not read old memory.json — starting fresh encrypted")

# Create fresh encrypted agent
agent = AgentMemory()

# Migrate key fields
if old_data:
    agent.state.current_session = old_data.get("current_session", "default")
    agent.state.tokens_used_session = old_data.get("tokens_used_session", 0)
    agent.state.stats.update(old_data.get("stats", {}))
    agent.state.sessions = old_data.get("sessions", {})
    agent.state.user_name = old_data.get("user_name")
    agent.state.session_turn_count = old_data.get("session_turn_count", {})
    agent.state.turns_since_last_journal = old_data.get("turns_since_last_journal", {})
    agent.state.total_xp = old_data.get("total_xp", 0)
    agent.state.level = old_data.get("level", 1)
    agent.state.xp_sources = old_data.get("xp_sources", {})
    agent.state.personality = old_data.get("personality", agent.state.personality)
    agent.state.omnipalace_rooms = old_data.get("omnipalace_rooms", {})
    agent.state.wiki_contributions = old_data.get("wiki_contributions", 0)

agent.save()
print("✅ Full migration to encrypted storage completed!")
print(f"New encrypted memory saved. Old backup at: {backup_dir}")

print("\nYou can now safely delete old unencrypted files if desired.")