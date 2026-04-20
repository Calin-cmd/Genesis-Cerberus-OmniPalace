"""
Genesis v5.6.9 — AgentState
Pure data + persistence layer. Single source of truth for all persistent state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from datetime import date
from collections import defaultdict
from pathlib import Path
from typing import Dict

from ..security.encryption import secure_storage
from ..config import CONFIG, STORAGE_PATH, STORAGE_DIR


@dataclass
class AgentState:
    """Pure persistent state for AgentMemory."""

    # Core conversation state
    sessions: Dict[str, list] = field(default_factory=dict)
    current_session: str = "default"
    session_budget: int = CONFIG.get("session_budget", 120000)
    tokens_used_session: int = 0

    # Consolidated Statistics
    stats: Dict = field(default_factory=lambda: {
        "total_memories": 0, "total_sessions": 0, "journals_run": 0,
        "predictions_run": 0, "coherences_run": 0, "decays_run": 0,
        "reflections_run": 0, "good_feedback": 0, "wrong_feedback": 0,
        "important_feedback": 0, "total_reward": 0.0, "policy_score": 0.5,
        "contradictions_detected": 0, "facts_merged": 0, "facts_archived": 0,
        "auto_dream_runs": 0, "proactive_runs": 0, "inspiration_bursts": 0,
        "wiki_compiles": 0, "wiki_heals": 0, "palace_growth_events": 0
    })

    # XP & Personality
    total_xp: int = 0
    level: int = 1
    xp_sources: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    personality: Dict[str, float] = field(default_factory=lambda: {
        "curiosity": 0.5, "empathy": 0.5, "strategic": 0.5,
        "resilience": 0.5, "creativity": 0.5
    })

    # Protected user_name
    _user_name: str = field(default="", repr=False)

    @property
    def user_name(self) -> str:
        return self._user_name

    @user_name.setter
    def user_name(self, value: str):
        if value and str(value).strip():
            cleaned = str(value).strip()
            if cleaned != self._user_name:
                self._user_name = cleaned
                self.mark_dirty()

    # ====================== MULTI-USER SUPPORT ======================
    current_user_id: str = "default"
    user_profiles: Dict[str, Dict] = field(default_factory=dict)

    # Social Graph (Phase 3.2)
    social_graph: Dict[str, Dict] = field(default_factory=dict)

    # Session tracking
    session_turn_count: Dict[str, int] = field(default_factory=dict)
    turns_since_last_journal: Dict[str, int] = field(default_factory=dict)
    last_rag_turn: int = 0
    last_date: date = field(default_factory=date.today)

    # Advanced fields
    omnipalace_rooms: Dict[str, Dict] = field(default_factory=dict)
    current_palace_room: str = "Entrance Hall"
    active_sub_agents: list = field(default_factory=list)
    persistent_sub_agents: Dict[str, Dict] = field(default_factory=dict)
    wiki_contributions: int = 0

    # Internal flags
    _dirty: bool = False
    _burst_triggered_this_turn: bool = False

    def mark_dirty(self):
        self._dirty = True

    def get_current_user_id(self) -> str:
        return self.current_user_id

    def save_if_changed(self) -> bool:
        if not self._dirty:
            return False
        try:
            data = {
                "current_session": self.current_session,
                "session_budget": self.session_budget,
                "tokens_used_session": self.tokens_used_session,
                "stats": dict(self.stats),
                "sessions": self.sessions,
                "user_name": self.user_name,
                "session_turn_count": self.session_turn_count,
                "turns_since_last_journal": self.turns_since_last_journal,
                "last_date": self.last_date.isoformat() if hasattr(self.last_date, 'isoformat') else str(self.last_date),
                "last_rag_turn": self.last_rag_turn,
                "total_xp": self.total_xp,
                "level": self.level,
                "xp_sources": dict(self.xp_sources),
                "personality": self.personality,
                "omnipalace_rooms": self.omnipalace_rooms,
                "current_palace_room": self.current_palace_room,
                "wiki_contributions": self.wiki_contributions,
                "active_sub_agents": self.active_sub_agents,
                "persistent_sub_agents": self.persistent_sub_agents,
                "current_user_id": self.current_user_id,
                "user_profiles": self.user_profiles,
                "social_graph": self.social_graph,
            }

            from ..security.encryption import secure_storage
            secure_storage.save_encrypted(STORAGE_PATH, data)
            self._dirty = False
            return True
        except Exception as e:
            print(f"[ENCRYPTED SAVE ERROR] {e}")
            return False

    @classmethod
    def load(cls) -> "AgentState":
        from ..security.encryption import secure_storage
        if not STORAGE_PATH.exists():
            return cls()
        try:
            data = secure_storage.load_encrypted(STORAGE_PATH)
            instance = cls()
            instance.current_session = data.get("current_session", "default")
            instance.session_budget = data.get("session_budget", CONFIG.get("session_budget", 120000))
            instance.tokens_used_session = data.get("tokens_used_session", 0)
            instance.stats.update(data.get("stats", {}))
            instance.sessions = data.get("sessions", {})
            instance.user_name = data.get("user_name", "")
            instance.session_turn_count = data.get("session_turn_count", {})
            instance.turns_since_last_journal = data.get("turns_since_last_journal", {})
            if "last_date" in data:
                instance.last_date = date.fromisoformat(data["last_date"])
            if "last_rag_turn" in data:
                instance.last_rag_turn = data["last_rag_turn"]
            if "total_xp" in data:
                instance.total_xp = data["total_xp"]
                instance.level = data.get("level", 1)
                instance.xp_sources = defaultdict(int, data.get("xp_sources", {}))
                instance.personality = data.get("personality", instance.personality)
            instance.omnipalace_rooms = data.get("omnipalace_rooms", {})
            instance.current_palace_room = data.get("current_palace_room", "Entrance Hall")
            instance.wiki_contributions = data.get("wiki_contributions", 0)
            instance.active_sub_agents = data.get("active_sub_agents", [])
            instance.persistent_sub_agents = data.get("persistent_sub_agents", {})
            instance._dirty = False
            instance.current_user_id = data.get("current_user_id", "default")
            instance.user_profiles = data.get("user_profiles", {})
            instance.social_graph = data.get("social_graph", {})
            print("[ENCRYPTION] Memory loaded successfully (encrypted)")
            return instance
        except Exception as e:
            print(f"[ENCRYPTED LOAD FAIL] {e} — Starting fresh")
            return cls()
