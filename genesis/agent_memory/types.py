"""
Genesis v5.6.9 Cerberus OmniPalace — Shared Types
Shared type definitions and dataclasses for cleaner code across modules.
"""

from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass


# Shared dataclasses
@dataclass
class MemoryEntry:
    """Standard memory entry structure"""
    content: str
    topic: str
    importance: float
    tags: List[str]
    timestamp: str
    id: str


@dataclass
class WikiPage:
    """Obsidian Wiki page structure"""
    title: str
    content: str
    frontmatter: Dict[str, Any]
    path: str
    backlinks: List[str]
    tags: List[str]
    last_updated: str


# Type aliases for better readability
LLMCall = Tuple[str, str, Optional[str]]           # (system_prompt, user_prompt, model)
RetrievalResult = Dict[str, Any]
ToolCallResult = Dict[str, Any]
PersonalityDict = Dict[str, float]
XPSourcesDict = Dict[str, int]
WikiEntry = Dict[str, Any]


# Common constants used across modules
DEFAULT_IMPORTANCE = 0.6
HIGH_IMPORTANCE = 0.85
JOURNAL_IMPORTANCE = 0.82
REFLECTION_IMPORTANCE = 0.80
WIKI_IMPORTANCE = 0.88   # New: Higher importance for Obsidian wiki entries


# For future extension
__all__ = [
    "MemoryEntry",
    "WikiPage",
    "LLMCall",
    "RetrievalResult",
    "ToolCallResult",
    "PersonalityDict",
    "XPSourcesDict",
    "WikiEntry",
    "DEFAULT_IMPORTANCE",
    "HIGH_IMPORTANCE",
    "JOURNAL_IMPORTANCE",
    "REFLECTION_IMPORTANCE",
    "WIKI_IMPORTANCE"
]


# For easy debugging
if __name__ == "__main__":
    print("Shared types loaded successfully.")
    print("Wiki types included.")