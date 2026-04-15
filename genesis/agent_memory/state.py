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

from ..config import CONFIG, STORAGE_PATH, STORAGE_DIR


@dataclass
class AgentState:
    """Pure persistent state for AgentMemory."""

    # Core conversation state
    sessions: Dict[str, list] = field(default_factory=dict)
    current_session: str = "default"
    session_budget: int = CONFIG.get("session_budget", 120000)
    tokens_used_session: int = 0

    # Statistics
    stats: Dict = field(default_factory=lambda: {
        "total_memories": 0, "total_sessions": 0, "journals_run": 0,
        "predictions_run": 0, "coherences_run": 0, "decays_run": 0,
        "reflections_run": 0, "good_feedback": 0, "wrong_feedback": 0,
        "important_feedback": 0, "total_reward": 0.0, "policy_score": 0.5,
        "contradictions_detected": 0, "facts_merged": 0, "facts_archived": 0,
        "auto_dream_runs": 0, "proactive_runs": 0, "inspiration_bursts": 0,
        "wiki_compiles": 0, "wiki_heals": 0,
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

    # Session tracking
    session_turn_count: Dict[str, int] = field(default_factory=dict)
    turns_since_last_journal: Dict[str, int] = field(default_factory=dict)
    last_rag_turn: int = 0
    last_date: date = field(default_factory=date.today)

    # Advanced fields
    omnipalace_rooms: Dict[str, Dict] = field(default_factory=dict)
    current_palace_room: str = "Entrance Hall"
    active_sub_agents: Dict[str, Dict] = field(default_factory=dict)
    persistent_sub_agents: Dict[str, Dict] = field(default_factory=dict)
    wiki_contributions: int = 0

    # Internal flags
    _dirty: bool = False
    _burst_triggered_this_turn: bool = False

    def mark_dirty(self):
        self._dirty = True

    def save_if_changed(self) -> bool:
        if not self._dirty:
            return False
        try:
            data = {
                "current_session": self.current_session,
                "session_budget": self.session_budget,
                "tokens_used_session": self.tokens_used_session,
                "stats": self.stats,
                "sessions": self.sessions,
                "user_name": self.user_name,
                "session_turn_count": self.session_turn_count,
                "turns_since_last_journal": self.turns_since_last_journal,
                "last_date": self.last_date.isoformat(),
                "last_rag_turn": self.last_rag_turn,
                "total_xp": self.total_xp,
                "level": self.level,
                "xp_sources": dict(self.xp_sources),
                "personality": self.personality,
                "omnipalace_rooms": self.omnipalace_rooms,
                "current_palace_room": self.current_palace_room,
                "wiki_contributions": self.wiki_contributions,
            }
            tmp = STORAGE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(STORAGE_PATH)
            self._dirty = False
            return True
        except Exception as e:
            print(f"[SAVE ERROR] {e}")
            return False

    @classmethod
    def load(cls) -> "AgentState":
        if not STORAGE_PATH.exists():
            return cls()
        try:
            raw = json.loads(STORAGE_PATH.read_text(encoding="utf-8"))
            instance = cls()
            instance.current_session = raw.get("current_session", "default")
            instance.session_budget = raw.get("session_budget", CONFIG.get("session_budget", 120000))
            instance.tokens_used_session = raw.get("tokens_used_session", 0)
            instance.stats.update(raw.get("stats", {}))
            instance.sessions = raw.get("sessions", {})
            instance.user_name = raw.get("user_name", "")
            instance.session_turn_count = raw.get("session_turn_count", {})
            instance.turns_since_last_journal = raw.get("turns_since_last_journal", {})
            if "last_date" in raw:
                instance.last_date = date.fromisoformat(raw["last_date"])
            if "last_rag_turn" in raw:
                instance.last_rag_turn = raw["last_rag_turn"]
            if "total_xp" in raw:
                instance.total_xp = raw["total_xp"]
                instance.level = raw.get("level", 1)
                instance.xp_sources = defaultdict(int, raw.get("xp_sources", {}))
                instance.personality = raw.get("personality", instance.personality)
            instance.omnipalace_rooms = raw.get("omnipalace_rooms", {})
            instance.current_palace_room = raw.get("current_palace_room", "Entrance Hall")
            instance.wiki_contributions = raw.get("wiki_contributions", 0)
            instance._dirty = False
            return instance
        except Exception as e:
            print(f"[LOAD FAIL] {e}")
            return cls()