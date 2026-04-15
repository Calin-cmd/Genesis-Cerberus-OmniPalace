"""
Genesis v5.6.9 — Full Persistence Layer
Restores conversation history, index, OmniPalace, and wiki state across sessions.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

from ..config import STORAGE_PATH, log_status, HALL_OF_RECORDS_DIR
from .core import AgentMemory


def save_agent_memory(agent: AgentMemory) -> bool:
    """Full atomic save of all important state."""
    try:
        data = {
            "version": "5.6.9",
            "timestamp": datetime.now().isoformat(),

            "user_name": getattr(agent, "user_name", ""),
            "level": getattr(agent, "level", 1),
            "total_xp": getattr(agent, "total_xp", 0),

            "current_session": getattr(agent, "current_session", "default"),
            "sessions": getattr(agent, "sessions", {}),
            "session_turn_count": getattr(agent, "session_turn_count", {}),
            "turns_since_last_journal": getattr(agent, "turns_since_last_journal", {}),
            "tokens_used_session": getattr(agent, "tokens_used_session", 0),
            "session_budget": getattr(agent, "session_budget", 120000),
            "last_rag_turn": getattr(agent, "last_rag_turn", 0),
            "last_date": getattr(agent.last_date, "isoformat", lambda: str(agent.last_date))(),

            "stats": getattr(agent, "stats", {}),
            "xp_sources": dict(getattr(agent, "xp_sources", {})),
            "personality": getattr(agent, "personality", {}),

            "omnipalace_rooms": getattr(agent, "omnipalace_rooms", {}),
            "current_palace_room": getattr(agent, "current_palace_room", "Entrance Hall"),
            "active_sub_agents": getattr(agent, "active_sub_agents", {}),
            "persistent_sub_agents": getattr(agent, "persistent_sub_agents", {}),
            "wiki_contributions": getattr(agent, "wiki_contributions", 0),
        }

        # Atomic write
        tmp = STORAGE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(STORAGE_PATH)

        # Force index save
        if hasattr(agent.index, 'save_index'):
            agent.index.save_index()

        agent._dirty = False

        wiki_count = agent.get_wiki_status().get("wiki_pages", 0) if hasattr(agent, 'get_wiki_status') else 0
        mem_count = len(getattr(agent.index, 'index_lines', []))

        log_status(f"[PERSISTENCE] Saved — Level {data['level']} | XP {data['total_xp']} | "
                   f"Wiki: {wiki_count} | Memories: {mem_count}")

        # === RESTORED VISION: Trigger Hall of Records archive when flagged ===
        if getattr(agent, '_should_archive', False):
            try:
                journal = getattr(agent.autonomous, '_create_journal_entry', lambda f=False: "No journal available")(force=True)
                archive_session_to_hall_of_records(agent, agent.current_session, journal)
                agent._should_archive = False
            except Exception as e:
                log_status(f"[PERSISTENCE] Archive warning: {e}")

        return True

    except Exception as e:
        print(f"[PERSISTENCE] Save error: {e}")
        return False


def load_agent_memory(cls: type[AgentMemory]) -> AgentMemory:
    """Full restore with rich memory index reload."""
    try:
        data = json.loads(STORAGE_PATH.read_text(encoding="utf-8")) if STORAGE_PATH.exists() else {}
    except Exception:
        data = {}

    agent = cls()   # This creates index, omnipalace, memory, etc.

    # Restore core state
    agent.user_name = data.get("user_name", "")
    agent.level = data.get("level", 1)
    agent.total_xp = data.get("total_xp", 0)
    agent.current_session = data.get("current_session", "default")
    agent.sessions = data.get("sessions", {})
    agent.session_turn_count = data.get("session_turn_count", {})
    agent.turns_since_last_journal = data.get("turns_since_last_journal", {})
    agent.tokens_used_session = data.get("tokens_used_session", 0)
    agent.session_budget = data.get("session_budget", 120000)
    agent.last_rag_turn = data.get("last_rag_turn", 0)

    if "last_date" in data:
        try:
            agent.last_date = date.fromisoformat(data["last_date"])
        except:
            pass

    agent.stats.update(data.get("stats", {}))
    agent.xp_sources = defaultdict(int, data.get("xp_sources", {}))
    agent.personality = data.get("personality", {k: 0.5 for k in ["curiosity","empathy","strategic","resilience","creativity"]})

    # Palace + Wiki
    agent.omnipalace_rooms = data.get("omnipalace_rooms", {})
    agent.current_palace_room = data.get("current_palace_room", "Entrance Hall")
    agent.wiki_contributions = data.get("wiki_contributions", 0)

    # === CRITICAL: Reload rich memory index ===
    if hasattr(agent.index, 'load_index'):
        agent.index.load_index()

    agent._dirty = False

    wiki_count = agent.get_wiki_status().get("wiki_pages", 0) if hasattr(agent, 'get_wiki_status') else 0
    mem_count = len(getattr(agent.index, 'index_lines', []))

    log_status(f"[PERSISTENCE] Loaded successfully — Level {agent.level} | XP {agent.total_xp:,} | "
               f"User: {agent.user_name or 'Unknown'} | Wiki: {wiki_count} | Memories: {mem_count}")

    return agent


def archive_session_to_hall_of_records(agent: AgentMemory, session_id: str, journal_text: str):
    """Core of the original vision: timestamped archive for later parsing.
    Saves raw session + human-readable journal to Hall of Records and routes to OmniPalace."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        hall_dir = HALL_OF_RECORDS_DIR
        hall_dir.mkdir(parents=True, exist_ok=True)

        # Raw session JSON (exact history for future parsing)
        raw_path = hall_dir / f"session_{session_id}_{ts}.json"
        raw_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "turns": agent.sessions.get(session_id, []),
            "journal": journal_text,
            "user_name": getattr(agent, "user_name", ""),
            "level": getattr(agent, "level", 1),
            "total_xp": getattr(agent, "total_xp", 0)
        }
        raw_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        # Human-readable journal Markdown
        md_path = hall_dir / f"journal_{session_id}_{ts}.md"
        md_content = f"""# Session Journal — {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}
**Session ID:** {session_id}
**User:** {getattr(agent, "user_name", "Unknown")}
**Level:** {getattr(agent, "level", 1)} | **XP:** {getattr(agent, "total_xp", 0)}
**Archived to Hall of Records**

{journal_text}

---
**Raw session data also archived as JSON for exact future parsing by Genesis.**
**This entry will be used for pre-warming persistent state on next session load.**
"""
        md_path.write_text(md_content, encoding="utf-8")

        # Route to OmniPalace Hall of Records
        if hasattr(agent, 'omnipalace'):
            agent.omnipalace.add_atomic(journal_text, tags=["journal", "session_archive", "hall_of_records"])
            agent.omnipalace.current_room = "Hall of Records"

        log_status(f"[HALL OF RECORDS] Archived session {session_id} → {md_path.name} + raw JSON")
        return str(md_path)

    except Exception as e:
        print(f"[HALL OF RECORDS] Archive error: {e}")
        return None