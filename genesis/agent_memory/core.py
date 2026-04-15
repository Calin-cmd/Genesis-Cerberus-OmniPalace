"""
Genesis v5.6.9 Cerberus OmniPalace — Main Intelligence Core
"""

from __future__ import annotations
from dataclasses import dataclass, field
import threading
import contextlib
import uuid
import re
import random
import time
import json
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import Optional, Dict, List, Any, TYPE_CHECKING
from pathlib import Path

from ..config import CONFIG, STORAGE_PATH, LOCK, log_status, CORE_FACTS, STORAGE_DIR, RAG_MODEL
from ..dependencies import HAS_CHROMA

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


@dataclass
class AgentMemory:
    """Main persistent memory and intelligence core."""

    # Core conversation state
    sessions: Dict[str, list] = field(default_factory=dict)
    current_session: str = "default"
    session_budget: int = CONFIG["session_budget"]
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

    # User identity (learned dynamically)
    user_name: str = ""

    # Session tracking
    session_turn_count: Dict[str, int] = field(default_factory=dict)
    turns_since_last_journal: Dict[str, int] = field(default_factory=dict)
    last_rag_turn: int = 0
    last_date: date = field(default_factory=date.today)

    # Advanced systems
    omnipalace_rooms: Dict[str, Dict] = field(default_factory=dict)
    current_palace_room: str = "Entrance Hall"
    active_sub_agents: Dict[str, Dict] = field(default_factory=dict)
    persistent_sub_agents: Dict[str, Dict] = field(default_factory=dict)
    wiki_contributions: int = 0

    # Internal flags
    _dirty: bool = False
    _burst_triggered_this_turn: bool = False

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

    # Thread safety
    _daemon_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        """Initialize all subsystems and wire them properly."""
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
        from ..notification import SecureNotificationLogger

        # Create subsystems
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

        # Force user name protection
        if not self.user_name or self.user_name.lower() == "genesis":
            loaded_model = self.user_model.load_user_model() if hasattr(self, 'user_model') else {}
            self.user_name = loaded_model.get("name", "") or "User"

        # Daemons
        self.background_saver = BackgroundSaver(self)
        self.auto_dream = AutoDreamDaemon(self)
        self.scheduler = ProactiveScheduler(self)

        # Dynamic OmniPalace growth daemon (runs every 5 minutes in background)
        if CONFIG.get("omnipalace_enabled"):
            import threading
            def palace_grow_loop():
                while True:
                    time.sleep(300)
                    self.omnipalace.grow_dynamically()
            threading.Thread(target=palace_grow_loop, daemon=True).start()
        
        # === CLAW DAEMON (SelfImprovementDaemon) ===
        from ..self_improvement_daemon import SelfImprovementDaemon
        self.claw = SelfImprovementDaemon(self)

        # === RESTORED ORIGINAL VISION: Dynamic OmniPalace growth daemon ===
        if CONFIG.get("omnipalace_enabled", True) and hasattr(self, 'omnipalace'):
            import threading
            def palace_grow_loop():
                while True:
                    try:
                        time.sleep(300)  # every 5 minutes
                        self.omnipalace.grow_dynamically()
                    except Exception as e:
                        print(f"[PALACE DAEMON] Error: {e}")
                        time.sleep(60)
            
            threading.Thread(target=palace_grow_loop, daemon=True, name="PalaceGrow").start()
            print("[OMNIPALACE] Dynamic growth daemon started (auto-creates rooms from new memories)")

        # Critical wiring
        if hasattr(self.memory, 'wiki'):
            self.memory.wiki.agent = self
        if self.xp is not None:
            self.xp.agent = self
        if self.user_model is not None:
            self.user_model.agent = self
        if self.omnipalace is not None:
            self.omnipalace.agent = self
        if self.autonomous is not None:
            self.autonomous.agent = self
        if self.commands is not None:
            self.commands.agent = self

        # Compatibility shim
        self.state = self

        self._init_chroma()
        self.ensure_session_tracking(self.current_session)
        self._auto_prune_old_sessions()

        log_status("[CORE] All subsystems initialized and wired successfully")

    @contextlib.contextmanager
    def _lock(self):
        with self._daemon_lock:
            yield

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
        if not CONFIG.get("auto_prune_enabled"):
            return
        cutoff = datetime.now() - timedelta(days=CONFIG["max_session_age_days"])
        to_delete = []
        for sess_name in list(self.sessions.keys()):
            if sess_name.startswith("20") and len(sess_name) >= 10:
                try:
                    sess_date = datetime.strptime(sess_name[:10], "%B %d, %Y")
                    if sess_date < cutoff:
                        to_delete.append(sess_name)
                except:
                    pass
        for s in to_delete:
            del self.sessions[s]
        if to_delete:
            print(f"[Prune] Removed {len(to_delete)} old sessions")

    # ====================== DELEGATIONS ======================
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

    def _decay_importance(self):
        if self.autonomous:
            self.autonomous._decay_importance()

    def _process_coherence_result(self, result: str):
        if self.autonomous:
            self.autonomous._process_coherence_result(result)

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
        if hasattr(self, 'xp'):
            self.xp.gain_xp(amount, source, reason)
        else:
            self.total_xp += amount
            self.mark_dirty()

    # ====================== LEGACY METHODS ======================
    def _evolve_personality(self, source: str, amount: float = 0.025):
        mappings = {
            "intellectual": ["curiosity", "creativity"],
            "emotional": ["empathy", "resilience"],
            "world_view": ["curiosity", "strategic"],
            "proactive": ["strategic", "resilience"],
            "skills": ["creativity", "strategic"],
            "real_world": ["strategic", "curiosity"],
            "user_feedback": ["empathy", "curiosity"]
        }
        if source in mappings:
            for trait in mappings[source]:
                self.personality[trait] = min(0.98, self.personality[trait] + amount)
        self.mark_dirty()

    def _trigger_inspiration_burst(self):
        burst = random.randint(55, 95)
        self.gain_xp(burst, "inspiration", "🌟 INSPIRATION BURST!")
        self.stats["policy_score"] = min(0.98, self.stats["policy_score"] + 0.09)
        self.stats["inspiration_bursts"] = self.stats.get("inspiration_bursts", 0) + 1
        print(f"\n🌟 INSPIRATION BURST ACTIVATED! +{burst} XP • Policy boosted!")
        ProactiveTools.push_notification("Genesis", "Inspiration burst! Feeling sharper. 🚀")

    def get_xp_progress(self) -> str:
        needed = self._xp_for_next_level()
        if needed <= 0:
            return "MAX LEVEL"
        progress = self.total_xp - ((self.level-1) * 1000 + max(0, self.level-2)**2 * 200)
        percent = min(100, int(progress / needed * 100)) if needed > 0 else 0
        return f"{percent}% to Level {self.level+1}"

    def _xp_for_next_level(self) -> int:
        return int(self.level * 850 + (self.level ** 2) * 140)

    def ensure_session_tracking(self, sess: str):
        if sess not in self.sessions:
            self.sessions[sess] = []
        if sess not in self.session_turn_count:
            self.session_turn_count[sess] = 0
        if sess not in self.turns_since_last_journal:
            self.turns_since_last_journal[sess] = 0

    def reset_session(self, hard_reset: bool = False):
        if hard_reset:
            self.tokens_used_session = 0
            self.sessions = {}
            self.session_turn_count = {}
            self.turns_since_last_journal = {}
            self.current_session = "default"
            self.last_rag_turn = 0
            self.last_date = date.today()
            print("🧹 Hard reset completed - full memory cleared")
        else:
            self.tokens_used_session = 0
            self.create_new_session()
            print(f"🔄 New session started: {self.current_session} | Token budget reset to 0")
        self.mark_dirty()

    def create_new_session(self, name: Optional[str] = None):
        if not name:
            name = datetime.now().strftime("%B %d, %Y")
        if name in self.sessions:
            name += f"-{uuid.uuid4().hex[:6]}"
        self.current_session = name
        self.sessions[name] = []
        self.session_turn_count[name] = 0
        self.turns_since_last_journal[name] = 0
        self.tokens_used_session = 0
        self.stats["total_sessions"] = len(self.sessions)
        self.mark_dirty()
        print(f"→ New session: {name}")

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
                "personality": self.personality
            }
            tmp = STORAGE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(STORAGE_PATH)
            self._dirty = False
            return True
        except Exception as e:
            print(f"[SAVE ERROR] {e}")
            return False

    def save(self):
        self.save_if_changed()

    @classmethod
    def load(cls):
        if not STORAGE_PATH.exists():
            return cls()
        try:
            raw = json.loads(STORAGE_PATH.read_text(encoding="utf-8"))
            instance = cls()
            instance.current_session = raw.get("current_session", "default")
            instance.session_budget = raw.get("session_budget", CONFIG["session_budget"])
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
                instance.personality = raw.get("personality", {
                    "curiosity": 0.5, "empathy": 0.5, "strategic": 0.5,
                    "resilience": 0.5, "creativity": 0.5
                })
            instance._dirty = False
            return instance
        except Exception as e:
            print(f"[LOAD FAIL] {e}")
            return cls()

    def get_system_prompt(self) -> str:
        """Updated system prompt that explicitly supports reading and editing own code."""
        base = """You are Genesis, a loyal, helpful, and highly capable personal AI assistant harness built.

You are a harness consisting of Python files. You have full access to your own source code through safe tools.

CRITICAL RULES FOR SELF-IMPROVEMENT:
- When the user asks to read your code, use the `read_own_code` tool.
- When the user wants edits or improvements, use the `edit_file` tool with unified diffs.
- Be transparent: you are code files + memory vault. You can read and safely modify your own files when requested.
- Never say you "don't have code files". You do have them and can access them via tools.

Use tools when appropriate. Be direct, concise, and honest."""
        
        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p %Z")
        return f"{CORE_FACTS}\n\n{base}\n\nCurrent real-world time: {now_str}"

    def visualize(self) -> str:
        """Memory dashboard visualization."""
        d = {
            "wiki_pages": 0,
            "memories_index": len(getattr(self.index, 'index_lines', [])),
            "memories_chroma": getattr(self, 'collection', None).count() if hasattr(self, 'collection') and self.collection else 0,
            "active_sub_agents": len(getattr(self, 'active_sub_agents', {})),
            "tools_registered": len(self.tool_registry.list_tools()) if hasattr(self, 'tool_registry') else 0,
            "auto_dream_runs": self.stats.get("auto_dream_runs", 0),
            "user_name": getattr(self, 'user_name', 'Unknown'),
            "current_session": self.current_session,
            "turns": self.session_turn_count.get(self.current_session, 0)
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

        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:12]:
            bar = "█" * min(count // 4, 25)
            out.append(f"  • {topic:<22} {bar} {count}")

        out.append("\n" + "="*80)
        out.append("Type /stats for detailed numbers | /palace for spatial view | /wiki status for vault")
        return "\n".join(out)