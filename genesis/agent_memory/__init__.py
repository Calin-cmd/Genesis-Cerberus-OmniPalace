"""
Genesis v5.6.9 Cerberus OmniPalace
agent_memory sub-package entry point — re-exports key classes for clean imports.
"""

from __future__ import annotations

__version__ = "5.6.9"
__author__ = "Genesis Team"

# Re-export main classes for easy top-level imports
# Example: from genesis.agent_memory import AgentMemory, CerberusOrchestrator

from .core import AgentMemory
from .conversation import ConversationManager
from .state import AgentState
from .memory_index import MemoryIndex
from .memory import MemoryManager
from .llm import LLMManager
from .xp import XPManager
from .autonomous import AutonomousManager
from .commands import CommandRouter
from .user_model import UserModelManager
from .omnipalace_integration import OmniPalaceManager
from .tools import ToolRegistry
from .rag import AdvancedRAG

from ..cerberus import CerberusOrchestrator
from ..config import (
    CONFIG,
    RAG_MODEL,
    CORE_FACTS,
    HELP_TEXT,
    FULL_HELP_TEXT,
    log_status,
    STORAGE_DIR,
)

from ..dependencies import (
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

# Make the most important classes and utilities available at the sub-package level
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