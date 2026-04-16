"""
Genesis v5.6.9 Cerberus OmniPalace — Main Intelligence Core (Orchestrator)
Thin facade. Everything possible is delegated to AgentState or subsystems.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import threading
import contextlib
import time
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from collections import defaultdict

from ..config import CONFIG, log_status, CORE_FACTS, RAG_MODEL, STORAGE_DIR
from ..dependencies import HAS_CHROMA
from .state import AgentState

if TYPE_CHECKING:
    from .memory import MemoryManager
    from .llm import LLMManager
    from .xp import XPManager
    from .autonomous import AutonomousManager
    from .commands import CommandRouter
    from .user_model import UserModelManager
    from .omnipalace_integration import OmniPalaceManager
    from .memory_index import MemoryIndex
    from ..cerberus import CerberusOrchestrator
    from ..daemons import BackgroundSaver, AutoDreamDaemon, ProactiveScheduler
    from ..self_improvement_daemon import SelfImprovementDaemon
    from .tools import ToolRegistry
    from ..notification import ProactiveTools


@dataclass
class AgentMemory:
    """Thin orchestrator facade - public API remains stable."""

    state: AgentState = field(default_factory=AgentState)

    # Subsystems
    index: Optional["MemoryIndex"] = field(default=None, repr=False)
    memory: Optional["MemoryManager"] = field(default=None, repr=False)
    cerberus: Optional["CerberusOrchestrator"] = field(default=None, repr=False)
    omnipalace: Optional["OmniPalaceManager"] = field(default=None, repr=False)
    autonomous: Optional["AutonomousManager"] = field(default=None, repr=False)
    tool_registry: Optional["ToolRegistry"] = field(default=None, repr=False)
    commands: Optional["CommandRouter"] = field(default=None, repr=False)
    user_model: Optional["UserModelManager"] = field(default=None, repr=False)
    llm: Optional["LLMManager"] = field(default=None, repr=False)
    xp: Optional["XPManager"] = field(default=None, repr=False)

    # Daemons
    background_saver: Optional["BackgroundSaver"] = field(default=None, repr=False)
    auto_dream: Optional["AutoDreamDaemon"] = field(default=None, repr=False)
    scheduler: Optional["ProactiveScheduler"] = field(default=None, repr=False)
    claw: Optional["SelfImprovementDaemon"] = field(default=None, repr=False)

    _daemon_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        from .memory_index import MemoryIndex
        from .memory import MemoryManager
        from ..cerberus import CerberusOrchestrator
        from .omnipalace_integration import OmniPalaceManager
        from .autonomous import AutonomousManager
        from .tools import ToolRegistry
        from .commands import CommandRouter
        from .user_model import UserModelManager
        from .llm import LLMManager
        from .xp import XPManager
        from ..daemons import BackgroundSaver, AutoDreamDaemon, ProactiveScheduler
        from ..self_improvement_daemon import SelfImprovementDaemon

        self.index = MemoryIndex(self)
        self.memory = MemoryManager(self)
        self.cerberus = CerberusOrchestrator(self)
        self.omnipalace = OmniPalaceManager(self)
        self.autonomous = AutonomousManager(self)
        self.tool_registry = ToolRegistry(self)
        self.commands = CommandRouter(self)
        self.user_model = UserModelManager(self)
        self.llm = LLMManager(self)
        self.xp = XPManager(self)

        self.background_saver = BackgroundSaver(self)
        self.auto_dream = AutoDreamDaemon(self)
        self.scheduler = ProactiveScheduler(self)
        self.claw = SelfImprovementDaemon(self)

        # User name protection
        if not self.state.user_name or self.state.user_name.lower() == "genesis":
            loaded = self.user_model.load_user_model() if self.user_model else {}
            self.state.user_name = loaded.get("name", "") or "User"

        # Palace daemon
        if CONFIG.get("omnipalace_enabled", True) and self.omnipalace:
            threading.Thread(target=self._palace_grow_loop, daemon=True, name="PalaceGrow").start()
            print("[OMNIPALACE] Dynamic growth daemon started.")

        # Wiring
        if hasattr(self.memory, 'wiki'):
            self.memory.wiki.agent = self
        if self.xp: self.xp.agent = self
        if self.user_model: self.user_model.agent = self
        if self.omnipalace: self.omnipalace.agent = self
        if self.autonomous: self.autonomous.agent = self
        if self.commands: self.commands.agent = self

        self._init_chroma()
        self.ensure_session_tracking(self.state.current_session)
        self._auto_prune_old_sessions()

        log_status(f"[CORE] AgentMemory initialized — Level {self.level} | Tools: {len(self.tool_registry.list_tools()) if self.tool_registry else 0}")

    def _palace_grow_loop(self):
        while True:
            try:
                time.sleep(300)
                if self.omnipalace:
                    self.omnipalace.grow_dynamically()
            except Exception as e:
                print(f"[PALACE DAEMON] Error: {e}")
                time.sleep(60)

    @contextlib.contextmanager
    def _lock(self):
        with self._daemon_lock:
            yield

    # ====================== COMPLETE PROPERTY DELEGATIONS ======================
    @property
    def level(self): return self.state.level
    @level.setter
    def level(self, value): 
        self.state.level = value
        self.state.mark_dirty()

    @property
    def total_xp(self): return self.state.total_xp
    @total_xp.setter
    def total_xp(self, value): 
        self.state.total_xp = value
        self.state.mark_dirty()

    @property
    def xp_sources(self): return self.state.xp_sources
    @xp_sources.setter
    def xp_sources(self, value): 
        self.state.xp_sources = value
        self.state.mark_dirty()

    @property
    def personality(self): return self.state.personality
    @personality.setter
    def personality(self, value): 
        self.state.personality = value
        self.state.mark_dirty()

    @property
    def user_name(self): return self.state.user_name
    @user_name.setter
    def user_name(self, value): self.state.user_name = value

    @property
    def current_session(self): return self.state.current_session
    @current_session.setter
    def current_session(self, value): self.state.current_session = value

    @property
    def stats(self): return self.state.stats
    @stats.setter
    def stats(self, value): self.state.stats = value

    @property
    def sessions(self): return self.state.sessions
    @sessions.setter
    def sessions(self, value): self.state.sessions = value

    @property
    def session_turn_count(self): return self.state.session_turn_count
    @session_turn_count.setter
    def session_turn_count(self, value): self.state.session_turn_count = value

    @property
    def turns_since_last_journal(self): return self.state.turns_since_last_journal
    @turns_since_last_journal.setter
    def turns_since_last_journal(self, value): self.state.turns_since_last_journal = value

    @property
    def omnipalace_rooms(self): return self.state.omnipalace_rooms
    @omnipalace_rooms.setter
    def omnipalace_rooms(self, value): self.state.omnipalace_rooms = value

    @property
    def active_sub_agents(self): return self.state.active_sub_agents
    @active_sub_agents.setter
    def active_sub_agents(self, value): self.state.active_sub_agents = value

    @property
    def wiki_contributions(self): return self.state.wiki_contributions
    @wiki_contributions.setter
    def wiki_contributions(self, value): self.state.wiki_contributions = value

    # ====================== STATE METHODS ======================
    def mark_dirty(self): self.state.mark_dirty()
    def save_if_changed(self): return self.state.save_if_changed()
    def save(self): self.save_if_changed()

    @classmethod
    def load(cls):
        state = AgentState.load()
        return cls(state=state)

    # ====================== SESSION LIFECYCLE ======================
    def create_new_session(self, name: Optional[str] = None):
        if not name:
            name = datetime.now().strftime("%B %d, %Y")
        if name in self.state.sessions:
            name += f"-{uuid.uuid4().hex[:6]}"
        self.state.current_session = name
        self.state.sessions[name] = []
        self.state.session_turn_count[name] = 0
        self.state.turns_since_last_journal[name] = 0
        self.state.tokens_used_session = 0
        self.state.stats["total_sessions"] = len(self.state.sessions)
        self.mark_dirty()
        print(f"→ New session: {name}")

    def reset_session(self, hard_reset: bool = False):
        if hard_reset:
            self.state.tokens_used_session = 0
            self.state.sessions = {}
            self.state.session_turn_count = {}
            self.state.turns_since_last_journal = {}
            self.state.current_session = "default"
            self.state.last_rag_turn = 0
            self.state.last_date = date.today()
            print("🧹 Hard reset completed - full memory cleared")
        else:
            self.create_new_session()
            print(f"🔄 New session started: {self.state.current_session} | Token budget reset")
        self.mark_dirty()

    def ensure_session_tracking(self, sess: str):
        if sess not in self.state.sessions:
            self.state.sessions[sess] = []
        if sess not in self.state.session_turn_count:
            self.state.session_turn_count[sess] = 0
        if sess not in self.state.turns_since_last_journal:
            self.state.turns_since_last_journal[sess] = 0

    def _auto_prune_old_sessions(self):
        if not CONFIG.get("auto_prune_enabled"):
            return
        # (full logic can stay here or move to lifecycle.py later)
        pass  # placeholder - original logic can be added back if needed

    # ====================== REMAINING LEGACY METHODS ======================
    def _evolve_personality(self, source: str, amount: float = 0.025):
        mappings = { ... }  # copy from original if still used
        self.mark_dirty()

    def _trigger_inspiration_burst(self):
        burst = random.randint(55, 95)
        self.gain_xp(burst, "inspiration", "🌟 INSPIRATION BURST!")
        self.stats["policy_score"] = min(0.98, self.stats["policy_score"] + 0.09)
        self.stats["inspiration_bursts"] = self.stats.get("inspiration_bursts", 0) + 1
        print(f"\n🌟 INSPIRATION BURST ACTIVATED! +{burst} XP • Policy boosted!")
        ProactiveTools.push_notification("Genesis", "Inspiration burst! Feeling sharper. 🚀")

    def get_xp_progress(self) -> str:
        return self.xp.get_xp_progress() if self.xp and hasattr(self.xp, 'get_xp_progress') else "N/A"

    # ====================== CORE DELEGATIONS ======================
    def mark_dirty(self): self.state.mark_dirty()
    def save_if_changed(self): return self.state.save_if_changed()
    def save(self): self.save_if_changed()

    @classmethod
    def load(cls):
        state = AgentState.load()
        return cls(state=state)

    def create_new_session(self, name: Optional[str] = None):
        # Will be fully moved to lifecycle later
        print(f"→ New session: {self.state.current_session}")

    def reset_session(self, hard_reset: bool = False):
        print("Session reset requested")

    def ensure_session_tracking(self, sess: str):
        pass

    def add(self, content: str, topic: str = "general", importance: float = 0.6, tags: List[str] = None):
        return self.memory.add(content, topic, importance, tags) if self.memory else None

    def call_llm_safe(self, system: str, prompt: str, model=None):
        return self.llm.generate(system, prompt, model) if self.llm else "LLM unavailable."

    def get_recent_context(self) -> str:
        return self.memory.get_recent_context() if self.memory else ""

    def run_reflection(self, force: bool = False):
        return self.autonomous._run_reflection(force) if self.autonomous else ""

    def generate_forward_predictions(self, force: bool = False):
        return self.autonomous.generate_forward_predictions(force) if self.autonomous else ""

    def run_autonomous_nudge(self):
        return self.autonomous.run_autonomous_nudge() if self.autonomous else ""

    def run_coherence_check(self):
        return self.autonomous.run_coherence_check() if self.autonomous else ""

    def compile_obsidian_vault(self, source_folder=None):
        return self.memory.compile_obsidian_vault(source_folder) if self.memory else "Wiki unavailable."

    def heal_wiki(self, depth: str = "light"):
        return self.memory.heal_wiki(depth) if self.memory else "Wiki healing unavailable."

    def get_wiki_status(self) -> dict:
        return self.memory.get_wiki_status() if self.memory else {"wiki_pages": 0}

    def get_stats(self) -> str:
        return self.xp.get_stats() if self.xp else "Stats unavailable."

    def apply_feedback(self, cmd: str, entry_id: str = None):
        return self.xp.apply_feedback(cmd, entry_id) if self.xp else "Feedback unavailable."

    def gain_xp(self, amount: int, source: str = "general", reason: str = ""):
        if self.xp:
            self.xp.gain_xp(amount, source, reason)
        else:
            self.state.total_xp += amount
            self.mark_dirty()

    def get_system_prompt(self) -> str:
        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p %Z")
        return f"{CORE_FACTS}\n\nCurrent real-world time: {now_str}"

    def visualize(self) -> str:
        """Full restored dashboard visualization with topic distribution."""
        d = {
            "wiki_pages": 0,
            "memories_index": len(getattr(self.index, 'index_lines', [])),
            "memories_chroma": getattr(self, 'collection', None).count() if hasattr(self, 'collection') and self.collection else 0,
            "active_sub_agents": len(getattr(self, 'active_sub_agents', {})),
            "tools_registered": len(self.tool_registry.list_tools()) if self.tool_registry else 0,
            "auto_dream_runs": self.state.stats.get("auto_dream_runs", 0),
            "user_name": self.state.user_name or 'Unknown',
            "current_session": self.state.current_session,
            "turns": self.state.session_turn_count.get(self.state.current_session, 0)
        }

        topic_counts = defaultdict(int)
        for line in getattr(self.index, 'index_lines', [])[-500:]:
            try:
                topic = line.split(" | ")[1] if " | " in line else "general"
                topic_counts[topic] += 1
            except:
                pass

        out = [
            "="*80,
            f"          GENESIS v5.6.9 CERBERUS DASHBOARD — Level {self.level}",
            "="*80,
            f"XP: {self.total_xp:,} | Progress: {self.get_xp_progress() if hasattr(self, 'get_xp_progress') else 'N/A'} | Policy: {self.stats.get('policy_score', 0.5):.3f}",
            f"Obsidian Wiki: {d['wiki_pages']} pages | Memories: {d['memories_index']} (index) + {d['memories_chroma']} (Chroma)",
            f"OmniPalace Rooms: {len(self.omnipalace_rooms)} | Active Sub-Agents: {d['active_sub_agents']}",
            f"Tools: {d['tools_registered']} | AutoDream: {d['auto_dream_runs']} runs",
            f"User: {d['user_name']} | Session: {d['current_session']} ({d['turns']} turns)",
            "="*80,
            "\nTOPIC DISTRIBUTION (last 500 memories)",
        ]

        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:15]:
            bar = "█" * min(count // 4, 30)
            out.append(f"  • {topic:<25} {bar} {count}")

        out.append("\n" + "="*80)
        out.append("Type /stats for detailed numbers | /palace for spatial view | /wiki status for vault")
        return "\n".join(out)

    def _init_chroma(self):
        if not HAS_CHROMA:
            return
        try:
            import chromadb
            from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
            ef = OllamaEmbeddingFunction(
                model_name=CONFIG["ollama_embedding_model"],
                url=CONFIG["ollama_url"]
            )
            self.chroma_client = chromadb.PersistentClient(str(STORAGE_DIR / "chroma"))
            self.collection = self.chroma_client.get_or_create_collection(
                name="agent_memories", embedding_function=ef
            )
        except Exception as e:
            print(f"[CHROMA] Disabled: {e}")
            self.collection = None

    def _auto_prune_old_sessions(self):
        pass