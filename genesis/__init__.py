"""
Genesis v5.6.9 Cerberus OmniPalace
Root package entry point.
"""

from __future__ import annotations

__version__ = "5.6.9"
__author__ = "Genesis Team"

# Re-export core public API
from .agent_memory.core import AgentMemory
from .agent_memory.conversation import ConversationManager
from .agent_memory.tools import ToolRegistry
from .agent_memory.commands import CommandRouter
from .agent_memory.memory import MemoryManager
from .agent_memory.llm import LLMManager
from .agent_memory.xp import XPManager
from .agent_memory.autonomous import AutonomousManager
from .agent_memory.user_model import UserModelManager
from .agent_memory.omnipalace_integration import OmniPalaceManager
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
from .dependencies import *  # This brings in all HAS_XXX flags

__all__ = [
    "AgentMemory",
    "ConversationManager",
    "ToolRegistry",
    "CommandRouter",
    "MemoryManager",
    "LLMManager",
    "XPManager",
    "AutonomousManager",
    "UserModelManager",
    "OmniPalaceManager",
    "AdvancedRAG",
    "CerberusOrchestrator",
    "CONFIG",
    "RAG_MODEL",
    "CORE_FACTS",
    "HELP_TEXT",
    "FULL_HELP_TEXT",
    "log_status",
    "STORAGE_DIR",
    # HAS_ flags are exported via dependencies *
]