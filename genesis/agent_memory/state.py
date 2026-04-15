"""
Genesis v5.6.9 — AgentState
Pure data container for all persistent state. 
Fully updated with protected user_name property for maximum persistence safety
and Obsidian Vault awareness.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from collections import defaultdict
from typing import Dict, Any


@dataclass
class AgentState:
    """Pure data container for AgentMemory state with Wiki support."""

    # Core conversation state
    sessions: Dict[str, list] = field(default_factory=dict)
    current_session: str = "default"
    session_budget: int = 120000
    tokens_used_session: int = 0

    # Statistics
    stats: Dict = field(default_factory=lambda: {
        "total_memories": 0,
        "total_sessions": 0,
        "journals_run": 0,
        "predictions_run": 0,
        "coherences_run": 0,
        "decays_run": 0,
        "reflections_run": 0,
        "good_feedback": 0,
        "wrong_feedback": 0,
        "important_feedback": 0,
        "total_reward": 0.0,
        "policy_score": 0.5,
        "contradictions_detected": 0,
        "facts_merged": 0,
        "facts_archived": 0,
        "auto_dream_runs": 0,
        "proactive_runs": 0,
        "inspiration_bursts": 0,
        "wiki_compiles": 0,
        "wiki_heals": 0,
    })

    # XP & Personality System
    total_xp: int = 0
    level: int = 1
    xp_sources: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    personality: Dict[str, float] = field(default_factory=lambda: {
        "curiosity": 0.5,
        "empathy": 0.5,
        "strategic": 0.5,
        "resilience": 0.5,
        "creativity": 0.5
    })

    # Protected user_name (critical for persistence)
    _user_name: str = ""

    @property
    def user_name(self) -> str:
        """Protected getter for user_name"""
        return self._user_name

    @user_name.setter
    def user_name(self, value: str):
        """Protected setter — only allows non-empty names and marks dirty"""
        if value and str(value).strip():
            cleaned = str(value).strip()
            if cleaned != self._user_name:
                self._user_name = cleaned
                self._dirty = True

    # Session tracking
    session_turn_count: Dict[str, int] = field(default_factory=dict)
    turns_since_last_journal: Dict[str, int] = field(default_factory=dict)
    last_rag_turn: int = 0
    last_date: date = field(default_factory=date.today)

    # Caches
    _recent_rag_cache: Dict = field(default_factory=dict)

    # Advanced / Palace fields
    _burst_triggered_this_turn: bool = False
    _last_search_journal_time: float = 0.0
    _last_important_reflection_time: float = 0.0
    _last_subagent_spawn_time: float = 0.0
    _agent_counter: int = 0

    active_sub_agents: Dict[str, Dict] = field(default_factory=dict)
    persistent_sub_agents: Dict[str, Dict] = field(default_factory=dict)
    max_concurrent_agents: int = 4

    omnipalace_rooms: Dict[str, Dict] = field(default_factory=dict)
    current_palace_room: str = "Entrance Hall"

    # Obsidian Vault fields
    last_wiki_compile: str = ""
    wiki_contributions: int = 0

    # Internal dirty flag for persistence
    _dirty: bool = False


# For easy debugging
if __name__ == "__main__":
    state = AgentState()
    print("AgentState loaded successfully.")
    print(f"Default user_name: '{state.user_name}'")
    state.user_name = "User"
    print(f"After setting name: '{state.user_name}'")
    print("All fields initialized correctly.")
    print(f"Wiki contributions field: {state.wiki_contributions}")