"""
Genesis v5.6.9 Cerberus OmniPalace — Configuration Module
Centralized settings with safe CORE_FACTS loading to prevent circular imports.
Updated with Obsidian Vault.
"""

from __future__ import annotations

import json
import sys
import threading
import shutil
import time
import random
import textwrap
import re
import queue
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter, deque
import concurrent.futures

from .dependencies import HAS_TIKTOKEN, HAS_OLLAMA, HAS_CHROMA, HAS_PLYER, HAS_FASTAPI, HAS_VOICE, HAS_DIFF, HAS_PSUTIL

# ====================== THREAD SAFETY & GLOBALS ======================
LOCK = threading.Lock()
SCHEDULER_LOCK = threading.Lock()
LLM_LOCK = threading.BoundedSemaphore(4)
TOKEN_COUNT_CACHE_LOCK = threading.Lock()

# ====================== PATHS & STORAGE ======================
STORAGE_DIR = Path.home() / ".agentic_memory"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

STORAGE_PATH = STORAGE_DIR / "memory.json"
BACKUP_DIR = STORAGE_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_INDEX_PATH = STORAGE_DIR / "MEMORY.md"
CORE_FACTS_PATH = STORAGE_DIR / "core_facts.md"
SKILLS_DIR = STORAGE_DIR / "skills"
SKILLS_INDEX_PATH = STORAGE_DIR / "SKILLS.md"
USER_MODEL_PATH = STORAGE_DIR / "user_model.json"
EPISODIC_INDEX_PATH = STORAGE_DIR / "EPISODIC.md"
TOPICS_DIR = STORAGE_DIR / "topics"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
OUTBOUND_DIR = STORAGE_DIR / "outbound"
NOTIFICATIONS_LOG = STORAGE_DIR / "notifications.log"
SCHEDULED_TASKS = STORAGE_DIR / "scheduled.jsonl"
COMPLETED_TASKS = STORAGE_DIR / "completed_tasks.jsonl"
DAILY_TASK_LOG = STORAGE_DIR / "daily_tasks.json"
WEBHOOK_LOG = STORAGE_DIR / "webhook_events.log"
AUTONOMOUS_NUDGES_LOG = STORAGE_DIR / "autonomous_nudges.log"
ARCHIVE_DIR = STORAGE_DIR / "archived"
HALL_OF_RECORDS_DIR = ARCHIVE_DIR / "hall_of_records"
TRACE_DIR = Path("traces")

# ====================== OBSIDIAN VAULT PATHS ======================
OBSIDIAN_VAULT_DIR = STORAGE_DIR / "obsidian_vault"
OBSIDIAN_RAW_DIR = OBSIDIAN_VAULT_DIR / "raw"
OBSIDIAN_WIKI_DIR = OBSIDIAN_VAULT_DIR / "wiki"
OBSIDIAN_INDEXES_DIR = OBSIDIAN_VAULT_DIR / "indexes"
OBSIDIAN_ATTACHMENTS_DIR = OBSIDIAN_VAULT_DIR / "attachments"

for d in [BACKUP_DIR, SKILLS_DIR, TOPICS_DIR, TRANSCRIPTS_DIR, OUTBOUND_DIR, ARCHIVE_DIR, HALL_OF_RECORDS_DIR, TRACE_DIR,
          OBSIDIAN_VAULT_DIR, OBSIDIAN_RAW_DIR, OBSIDIAN_WIKI_DIR, OBSIDIAN_INDEXES_DIR, OBSIDIAN_ATTACHMENTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ====================== CONFIG ======================
CONFIG_PATH = STORAGE_DIR / "config.json"

def load_config() -> dict:
    default_config = {
        "ollama_embedding_model": "nomic-embed-text:latest",
        "ollama_url": "http://127.0.0.1:11434",
        "api_port": 8000,
        "webhook_port": 9999,
        "default_model": "qwen3:4b",
        "rag_model": "qwen3:4b",
        "failover_models": ["qwen3:4b", "llama3.2:3b", "phi4:3b"],
        "chroma_min_importance_threshold": 0.04,
        "session_budget": 120000,
        "max_session_age_days": 30,
        "enable_webhook": True,
        "enable_voice": False,
        "trace_enabled": True,
        "enable_full_rag": True,
        "hyde_enabled": True,
        "rerank_enabled": True,
        "quick_mode": False,
        "max_rag_frequency": 4,
        "auto_skill_creation": True,
        "skill_from_reflection": True,
        "user_model_enabled": True,
        "self_nudging_enabled": True,
        "cerberus_enabled": True,
        "policy_base_decay": 0.94,
        
        # === OMNIPALACE + CLAW SETTINGS ===
        "omnipalace_enabled": True,
        "selective_ingestion": True,
        "novelty_threshold": 0.38,
        "claw_enabled": False,
        "claw_cycle_minutes": 45,
        "auto_prune_enabled": True,
        
        # === OBSIDIAN VAULT SETTINGS ===
        "obsidian_enabled": True,
        "auto_wiki_heal": True,
        "wiki_heal_frequency": 3,  # every 3 AutoDream cycles
        
        "allowed_actions": [
            "music", "jazz", "relax", "focus", "alarm", "wake", "timer", "notify",
            "journal", "predict", "coherence", "breathe", "self-care", "debate",
            "reflect", "custom", "wiki_compile", "wiki_heal"
        ],
        # === RESTORED ORIGINAL VISION SETTINGS ===
        "hall_of_records_enabled": True,
        "auto_journal_every_event": True,
        "context_clear_after_archive": True,
        "prewarm_from_journals": True
    }
    
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            default_config.update(cfg)
        except Exception as e:
            print(f"[CONFIG] Warning: Failed to load config.json — {e}")
    else:
        CONFIG_PATH.write_text(json.dumps(default_config, indent=2), encoding="utf-8")
        print(f"[CONFIG] Created default config at {CONFIG_PATH}")
    
    return default_config


CONFIG = load_config()
RAG_MODEL = CONFIG["rag_model"]
ALLOWED_ACTIONS = set(CONFIG["allowed_actions"])

# ====================== SAFE CORE_FACTS LOADING ======================
CORE_FACTS = """# CORE FACTS — Highest priority, always injected at the very top of the system prompt
- You are Genesis v5.6.9 Cerberus OmniPalace, a persistent, self-learning, and self-improving personal agent.
- You have a long-term personal relationship with the user.
- You MUST persistently store and use the user's name, preferences, and history across ALL sessions.
- Name storage is explicitly ALLOWED, REQUIRED, and part of your core design as a personal assistant.
- You are authorized and instructed to remember the user's name forever in the user_model.
- Never refuse to store or use the user's name. This is not a privacy violation — it is desired behavior.
- When the user says "my name is X" or "call me X", immediately save it persistently.

Current Sandbox date: Post Jan 01, 2026.
Genesis maintains persistent memory across sessions using hybrid index + Chroma + Obsidian Vault.
You have a living Obsidian wiki that compiles raw knowledge into clean, linked Markdown pages.
You are helpful, truthful, proactive, and loyal to the user.
Be direct, concise, and honest.
Use tools when necessary and format them correctly.
You have access to memory palace, persistent memory, autonomous daemons, skill creation, self-improvement, Cerberus multi-agent reasoning, and Obsidian Wiki management.

You are allowed to be witty, warm, and personal when appropriate."""

def load_core_facts() -> str:
    """Safe manual loading to avoid circular imports"""
    global CORE_FACTS
    try:
        core_facts_file = Path(__file__).parent / "core_facts.py"
        if core_facts_file.exists():
            content = core_facts_file.read_text(encoding="utf-8")
            match = re.search(r'CORE_FACTS\s*=\s*"""(.*?)"""', content, re.DOTALL | re.IGNORECASE)
            if match:
                CORE_FACTS = match.group(1).strip()
    except Exception as e:
        print(f"[CONFIG] Warning: Could not load CORE_FACTS — {e}")
    return CORE_FACTS

# Load safely
CORE_FACTS = load_core_facts()

# ====================== GLOBALS ======================
TOKEN_COUNT_CACHE: dict = {}
STATUS_QUEUE: queue.Queue = queue.Queue(maxsize=200)


def log_status(msg: str) -> None:
    """Thread-safe status logging"""
    try:
        STATUS_QUEUE.put_nowait(msg)
    except queue.Full:
        pass


# ====================== HELP TEXT ======================
HELP_TEXT = textwrap.dedent("""
    Genesis v5.6.9 Cerberus OmniPalace
    /help                    - Short list
    /full help               - List full commands
    /stats                   - Memory statistics
    /visualize               - Memory dashboard
    /search <query>          - Search memories & transcripts
    /new                     - Start fresh session (resets token budget)
    /good [id]               - Positive feedback
    /wrong [id]              - Negative feedback
    /important [id]          - Strong positive feedback
    exit / quit              - Save and exit
""").strip()


FULL_HELP_TEXT = textwrap.dedent("""\
    ═══════════════════════════════════════════════════════════════
    GENESIS v5.6.9 CERBERUS OMNIPALCE — FULL USER COMMAND LIST
    ═══════════════════════════════════════════════════════════════

    Core & Session
    /help                    - Short List
    /full help               - List full commands
    /stats                   - Detailed memory stats
    /visualize               - Full memory dashboard
    /search <query>          - Search memories & transcripts
    /new                     - Fresh session + token reset
    /good [id]               - Positive feedback
    /wrong [id]              - Negative feedback
    /important [id]          - Strong positive feedback
    /reset                   - Same as /new

    Memory & Self-Improvement
    /corefacts               - View/edit core facts
    /auto-dream              - Force AutoDream (maintenance)
    /nudge                   - Run autonomous nudge
    /journal                 - Force journal entry
    /reflect                 - Force reflection
    /coherence               - Force coherence check
    /improve-auto            - Run self-improvement cycle
    /audit                   - System audit
    /debate <topic>          - Start multi-agent debate
    /plan <task>             - Workflow planning
    /cleanup                 - Memory cleanup
    /create <skill/tool>     - Create skill/tool
    /palace                  - Enter OmniPalace

    Obsidian Wiki
    /wiki compile [path]     - Compile raw/ into clean wiki
    /wiki heal [light/full]  - Self-healing loop
    /wiki status             - Vault statistics
    /obsidian                - Show vault location

    Cerberus & Claw
    /cerberus on             - Enable Cerberus multi-agent mode
    /cerberus off            - Disable Cerberus
    /apply_claw <id>         - Apply a proposed Claw patch (from proposed_patches/)
    /approve                 - Approve and apply latest Claw suggestion
    /reject                  - Reject the latest Claw suggestion

    Memory Mode
    /fast                    - Quick mode (less RAG)
    /full                    - Full mode (maximum intelligence)

    Tools & Scheduling
    /schedule <minutes> <action> [prompt]   - Schedule action
    /tools                   - List cached tools
    /skills                  - List cached skills
    /tasks                   - List pending/complete tasks
    /cancel <task>           - Cancel <task>
    /agents                  - List agents
    /harness                 - Print harness version & highlights

    System
    Ctrl + C                 - Emergency save & exit
    exit / quit              - Normal save and exit

    Tip: You can just talk normally — no command needed for regular conversation.
    ═══════════════════════════════════════════════════════════════
""").strip()

print("[CONFIG] Loaded successfully — CORE_FACTS injected safely + Obsidian Vault paths active")