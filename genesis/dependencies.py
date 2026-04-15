"""
Genesis v5.6.9 Cerberus OmniPalace — Dependencies
Optional dependency checker and status reporting.
Updated with Obsidian-related notes.
"""

from __future__ import annotations

import sys

# ====================== OPTIONAL DEPENDENCIES ======================

# Core LLM & Embedding
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False
    ollama = None

# Vector Database
try:
    import chromadb
    from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False
    chromadb = None
    OllamaEmbeddingFunction = None

# Token counting
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    tiktoken = None

# Desktop notifications
try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False
    notification = None

# Web API
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = None
    CORSMiddleware = None
    BaseModel = None
    uvicorn = None

# Voice interface
try:
    import speech_recognition as sr
    import pyttsx3
    HAS_VOICE = True
except ImportError:
    HAS_VOICE = False
    sr = None
    pyttsx3 = None

# Diff patching (self-improvement)
try:
    import diff_match_patch
    HAS_DIFF = True
except ImportError:
    HAS_DIFF = False
    diff_match_patch = None

# System monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

# Web search tools
try:
    from duckduckgo_search import DDGS
    HAS_DUCKDUCKGO = True
except ImportError:
    HAS_DUCKDUCKGO = False
    DDGS = None

# Wikipedia
try:
    import wikipedia
    HAS_WIKIPEDIA = True
except ImportError:
    HAS_WIKIPEDIA = False
    wikipedia = None

# Tree-sitter for code parsing (Graphify / Karpathy mode)
try:
    from tree_sitter_languages import get_parser
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False
    get_parser = None

# Graph libraries for Leiden clustering
try:
    import networkx as nx
    from graspologic.partition import leiden
    HAS_GRAPH_LIBS = True
except ImportError:
    HAS_GRAPH_LIBS = False
    nx = None
    leiden = None


def print_dependency_status():
    """Print status of all optional dependencies"""
    print("\n=== GENESIS v5.6.9 DEPENDENCY STATUS ===")
    print(f"OLLAMA          : {'✅' if HAS_OLLAMA else '❌'}")
    print(f"CHROMA          : {'✅' if HAS_CHROMA else '❌'}")
    print(f"TIKTOKEN        : {'✅' if HAS_TIKTOKEN else '❌'}")
    print(f"PLYER (notify)  : {'✅' if HAS_PLYER else '❌'}")
    print(f"FASTAPI         : {'✅' if HAS_FASTAPI else '❌'}")
    print(f"VOICE           : {'✅' if HAS_VOICE else '❌'}")
    print(f"DIFF            : {'✅' if HAS_DIFF else '❌'}")
    print(f"PSUTIL          : {'✅' if HAS_PSUTIL else '❌'}")
    print(f"DUCKDUCKGO      : {'✅' if HAS_DUCKDUCKGO else '❌'}")
    print(f"WIKIPEDIA       : {'✅' if HAS_WIKIPEDIA else '❌'}")
    print(f"TREE-SITTER     : {'✅' if HAS_TREE_SITTER else '❌'} (for code AST)")
    print(f"GRAPH LIBS      : {'✅' if HAS_GRAPH_LIBS else '❌'} (Leiden clustering)")
    print("=======================================\n")


def check_critical_dependencies():
    """Warn about missing critical dependencies"""
    missing = []
    if not HAS_OLLAMA:
        missing.append("ollama (required for LLM)")
    if not HAS_CHROMA:
        print("[WARNING] ChromaDB is not installed — vector memory will be limited.")
    
    if missing:
        print("[CRITICAL] Missing required dependencies:")
        for m in missing:
            print(f"   • {m}")
        print("\nInstall with: pip install ollama chromadb tiktoken")
        # Do not exit — allow graceful degradation


# Auto-check on import
if __name__ != "__main__":
    check_critical_dependencies()