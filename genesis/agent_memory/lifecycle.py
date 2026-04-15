"""
Genesis - Lifecycle Management
Handles session tracking, pruning, chroma init, and persistence triggers.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from ..config import CONFIG, STORAGE_DIR


class AgentLifecycle:
    """Manages session lifecycle, pruning, and initialization tasks."""

    def __init__(self, agent: "AgentMemory"):
        self.agent = agent

    def ensure_session_tracking(self, sess: str):
        if sess not in self.agent.state.sessions:
            self.agent.state.sessions[sess] = []
        if sess not in self.agent.state.session_turn_count:
            self.agent.state.session_turn_count[sess] = 0
        if sess not in self.agent.state.turns_since_last_journal:
            self.agent.state.turns_since_last_journal[sess] = 0

    def create_new_session(self, name: str = None):
        if not name:
            name = datetime.now().strftime("%B %d, %Y")
        if name in self.agent.state.sessions:
            name += f"-{uuid.uuid4().hex[:6]}"
        
        self.agent.state.current_session = name
        self.agent.state.sessions[name] = []
        self.agent.state.session_turn_count[name] = 0
        self.agent.state.turns_since_last_journal[name] = 0
        self.agent.state.tokens_used_session = 0
        self.agent.state.stats["total_sessions"] = len(self.agent.state.sessions)
        self.agent.mark_dirty()
        print(f"→ New session: {name}")

    def reset_session(self, hard_reset: bool = False):
        if hard_reset:
            self.agent.state.tokens_used_session = 0
            self.agent.state.sessions = {}
            self.agent.state.session_turn_count = {}
            self.agent.state.turns_since_last_journal = {}
            self.agent.state.current_session = "default"
            self.agent.state.last_rag_turn = 0
            self.agent.state.last_date = datetime.now().date()
            print("🧹 Hard reset completed - full memory cleared")
        else:
            self.create_new_session()
            print(f"🔄 New session started: {self.agent.state.current_session} | Token budget reset")
        self.agent.mark_dirty()

    def _auto_prune_old_sessions(self):
        if not CONFIG.get("auto_prune_enabled"):
            return
        cutoff = datetime.now() - timedelta(days=CONFIG["max_session_age_days"])
        to_delete = []
        for sess_name in list(self.agent.state.sessions.keys()):
            if sess_name.startswith("20") and len(sess_name) >= 10:
                try:
                    sess_date = datetime.strptime(sess_name[:10], "%B %d, %Y")
                    if sess_date < cutoff:
                        to_delete.append(sess_name)
                except:
                    pass
        for s in to_delete:
            del self.agent.state.sessions[s]
        if to_delete:
            print(f"[Prune] Removed {len(to_delete)} old sessions")