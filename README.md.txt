# Genesis v5.6.9 Cerberus OmniPalace

**A modular, persistent, self-improving personal AI agent framework with hybrid memory, spatial memory palace, living Obsidian Wiki, and autonomous capabilities.**

## ✅ Restored Original Vision - April 2026

**Core persistence behaviors now active:**

- Every event triggers a timestamped journal → archived to Hall of Records
- Before session close / `/new` / shutdown: full journal + raw session archive
- Hall of Records journals are parsed on every new session for true pre-warming
- Context cache is automatically cleared while persistent memories (User/Self/World) are kept
- OmniPalace grows dynamically and auto-populates with tool results (web search, news, etc.)
- User name and facts are learned on every turn and stored persistently

All memories are timestamped, journaled, and spatially linked using method of loci.

---

## Overview

Genesis is a production-grade personal AI agent built in pure Python. It features long-term memory persistence, multi-agent reasoning (Cerberus), a spatial memory palace (OmniPalace), and a self-maintaining Obsidian Markdown knowledge vault.

### Core Design Principles
- **Full persistence** across restarts
- **Hybrid memory architecture** (flat index + vector + graph + spatial)
- **Autonomous operation** via background daemons
- **Self-modification capability** (Claw daemon + safe code editing)
- **Modular & extensible** plugin-style subsystems

---

## Architecture

### Main Components

| Module | Purpose | Key Classes |
|-------|--------|-----------|
| `agent_memory/core.py` | Central intelligence hub & state management | `AgentMemory` |
| `agent_memory/conversation.py` | Main conversation loop, prompt construction, tracing | `ConversationManager` |
| `agent_memory/memory.py` | Hybrid RAG, ChromaDB, Obsidian Wiki management | `MemoryManager`, `WikiManager` |
| `agent_memory/memory_index.py` | Flat index, graph metadata, archiving | `MemoryIndex` |
| `omnipalace_integration.py` | Spatial memory palace + atomic routing | `OmniPalaceManager` |
| `cerberus.py` | Multi-agent reasoning pipeline | `CerberusOrchestrator` |
| `tools.py` | Tool registry and safe execution | `ToolRegistry` |
| `autonomous.py` | Background behaviors (AutoDream, reflection, journaling) | `AutonomousManager` |
| `self_improvement_daemon.py` | Claw — autonomous code evolution | `SelfImprovementDaemon` |
| `xp.py` | XP, leveling, personality evolution, feedback | `XPManager` |
| `user_model.py` | Dynamic user profiling | `UserModelManager` |

### Data Flow

User Input → CommandRouter → ConversationManager → RAG + Preheat → LLM (with Cerberus option)
                  ↓
           MemoryIndex + Chroma + OmniPalace + Obsidian Wiki
                  ↓
          Autonomous Daemons (background)

---

## Project Structure

```bash
genesis-cerberus/
├── run.py                          # Main CLI entrypoint
├── genesis/
│   ├── __init__.py
│   ├── cerberus.py
│   ├── config.py
│   ├── core_facts.py
│   ├── daemons.py
│   ├── dependencies.py
│   ├── notification.py
│   ├── self_improvement.py
│   ├── self_improvement_daemon.py
│   ├── utils.py
│   ├── voice.py
│   ├── webhook.py
│   └── agent_memory/
│       ├── __init__.py
│       ├── api.py                  # FastAPI endpoints
│       ├── autonomous.py
│       ├── commands.py
│       ├── conversation.py
│       ├── core.py                 # AgentMemory dataclass + wiring
│       ├── llm.py
│       ├── memory.py               # Wiki + hybrid retrieval
│       ├── memory_index.py
│       ├── omnipalace_integration.py
│       ├── persistence.py
│       ├── rag.py
│       ├── state.py
│       ├── tools.py
│       ├── types.py
│       ├── user_model.py
│       └── xp.py
├── .gitignore
├── README.md
└── proposed_patches/               # Claw-generated patches

Key Technologies & DependenciesCore 
(Required):ollama — Local LLM inference
chromadb — Vector database

Optional / Enhanced:
fastapi + uvicorn — REST API
duckduckgo-search — Web & news search
plyer — Desktop notifications
diff_match_patch — Safe code patching
networkx + graspologic — Graph clustering (Leiden)
tree-sitter-languages — Code AST parsing

Running & Development
Basic Runbash

python run.py
python run.py --voice
python run.py --api --api-port 8000
python run.py --no-daemons     # For debugging

Important Flags & Commands
/stats — System statistics
/visualize — Memory palace dashboard
/wiki compile — Build Obsidian vault from raw/
/wiki heal [light/full] — Self-healing
/auto-dream — Manual maintenance cycle
/improve-auto — Trigger self-improvement
/apply_claw <id> — Apply Claw patch

Persistence Layer
All state is saved in ~/.agentic_memory/:memory.json — Core state
MEMORY.md — Human-readable index
obsidian_vault/ — Living knowledge base
chroma/ — Vector embeddings
traces/ — Rich internal thought tracing (for debugging & atomic fact extraction)

Extending Genesis
Adding a New ToolEdit genesis/agent_memory/tools.py
Add function in _register_default_tools()
Register with self.register(...)

Adding a New Room to OmniPalace
Edit OmniPalaceManager._init_default_rooms() in omnipalace_integration.pyCustom DaemonInherit from threading.Thread and register in core.py::__post_init__Self-Improvement (Claw)The Claw daemon runs in background during idle time and proposes safe patches.
Patches are saved to proposed_patches/ and applied manually via /apply_claw <id>.Development TipsEnable tracing: trace_enabled in config
Monitor logs via STATUS_QUEUE
Use /audit and /coherence for system health
Check ~/.agentic_memory/traces/ for internal reasoning

Roadmap (v6.0 Ideas)
Full GraphRAG with Leiden communities
Multi-modal (vision) support
Better 3D palace visualization (Three.js)
Plugin system
Docker + API-first deployment

Technical Contact / Maintainer: Calin Beale

Built as a long-term personal AI companion and knowledge system.

