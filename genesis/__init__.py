"""
Genesis v5.6.9 Cerberus OmniPalace
Root package entry point — re-exports key classes for clean imports.
"""

from __future__ import annotations

__version__ = "5.6.9"
__author__ = "Genesis Team"

# Re-export main classes for easy top-level imports
# Example: from genesis import AgentMemory, CerberusOrchestrator

from .agent_memory.core import AgentMemory
from .agent_memory.conversation import ConversationManager
from .agent_memory.state import AgentState
from .agent_memory.memory_index import MemoryIndex
from .agent_memory.memory import MemoryManager
from .agent_memory.llm import LLMManager
from .agent_memory.xp import XPManager
from .agent_memory.autonomous import AutonomousManager
from .agent_memory.commands import CommandRouter
from .agent_memory.user_model import UserModelManager
from .agent_memory.omnipalace_integration import OmniPalaceManager
from .agent_memory.tools import ToolRegistry
from .agent_memory.rag import AdvancedRAG

from .cerberus import CerberusOrchestrator
from .config import (
    CONFIG,
    RAG_MODEL,
    CORE_FACTS,
    HELP_TEXT,
    FULL_HELP_TEXT,
    log_status,
    STORAGE_DIR,
)

from .dependencies import (
    HAS_OLLAMA,
    HAS_CHROMA,
    HAS_TIKTOKEN,
    HAS_DIFF,
    HAS_FASTAPI,
    HAS_VOICE,
    HAS_PLYER,
    HAS_DUCKDUCKGO,
    HAS_WIKIPEDIA,
)

# Make the most important classes and utilities available at the root level
__all__ = [
    # Core
    "AgentMemory",
    "ConversationManager",
    "AgentState",
    "MemoryIndex",
    "MemoryManager",
    "LLMManager",
    "XPManager",
    "AutonomousManager",
    "CommandRouter",
    "UserModelManager",
    "OmniPalaceManager",
    "ToolRegistry",
    "AdvancedRAG",
    "CerberusOrchestrator",

    # Config & Utilities
    "CONFIG",
    "RAG_MODEL",
    "CORE_FACTS",
    "HELP_TEXT",
    "FULL_HELP_TEXT",
    "log_status",
    "STORAGE_DIR",

    # Dependencies
    "HAS_OLLAMA",
    "HAS_CHROMA",
    "HAS_TIKTOKEN",
    "HAS_DIFF",
    "HAS_FASTAPI",
    "HAS_VOICE",
    "HAS_PLYER",
    "HAS_DUCKDUCKGO",
    "HAS_WIKIPEDIA",
]