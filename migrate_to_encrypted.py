"""
One-time migration script: Move old unencrypted data to encrypted storage.
Run this once, then delete the file.
"""

from pathlib import Path
import json
import shutil
from datetime import date
from collections import defaultdict

# Import your modules
import sys
sys.path.insert(0, ".")

from genesis.config import STORAGE_PATH, STORAGE_DIR
from genesis.security.encryption import secure_storage
from genesis.agent_memory.state import AgentState

print("🔐 Starting migration to encrypted storage...")

backup_dir = STORAGE_DIR / "backup_pre_encryption"
backup_dir.mkdir(exist_ok=True)

# Backup old files
if STORAGE_PATH.exists():
    shutil.copy(STORAGE_PATH, backup_dir / "memory.json")
    print(f"✅ Backed up old memory.json to {backup_dir}")

# Load old data
if STORAGE_PATH.exists():
    try:
        old_data = json.loads(STORAGE_PATH.read_text(encoding="utf-8"))
        print(f"✅ Loaded {len(old_data.get('sessions', {}))} sessions from old file")
    except Exception as e:
        print(f"⚠️ Could not read old file: {e}")
        old_data = {}
else:
    old_data = {}

# Create new encrypted state
new_state = AgentState()

# Migrate key fields
new_state.current_session = old_data.get("current_session", "default")
new_state.session_budget = old_data.get("session_budget", 120000)
new_state.tokens_used_session = old_data.get("tokens_used_session", 0)
new_state.stats.update(old_data.get("stats", {}))
new_state.sessions = old_data.get("sessions", {})
new_state.user_name = old_data.get("user_name", "")
new_state.session_turn_count = old_data.get("session_turn_count", {})
new_state.turns_since_last_journal = old_data.get("turns_since_last_journal", {})
new_state.last_rag_turn = old_data.get("last_rag_turn", 0)
new_state.total_xp = old_data.get("total_xp", 0)
new_state.level = old_data.get("level", 1)
new_state.xp_sources = defaultdict(int, old_data.get("xp_sources", {}))
new_state.personality = old_data.get("personality", new_state.personality)
new_state.omnipalace_rooms = old_data.get("omnipalace_rooms", {})
new_state.current_palace_room = old_data.get("current_palace_room", "Entrance Hall")
new_state.wiki_contributions = old_data.get("wiki_contributions", 0)

if "last_date" in old_data:
    try:
        new_state.last_date = date.fromisoformat(old_data["last_date"])
    except:
        pass

# Save encrypted
new_state.save_if_changed()
print("✅ Migration to encrypted storage completed successfully!")

print(f"\nNew encrypted memory saved. Old backup at: {backup_dir}")
print("You can now safely delete the old unencrypted memory.json if desired.")