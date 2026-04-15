"""
Genesis v5.6.9 Cerberus OmniPalace — LLMManager
All LLM-related functionality with token counting, failover, and parallel calls.
Enhanced with Obsidian Wiki context awareness.
"""

from __future__ import annotations
import time
import concurrent.futures
from typing import List, Tuple, Optional

import ollama

from ..config import CONFIG, HAS_OLLAMA, LLM_LOCK, TOKEN_COUNT_CACHE_LOCK
from ..dependencies import HAS_TIKTOKEN


class LLMManager:
    """All LLM-related functionality with Obsidian Wiki integration."""

    def __init__(self, agent: "AgentMemory"):
        self.agent = agent
        self._tokenizer = None

    def call_llm(self, system: str, user: str, model: Optional[str] = None):
        """Basic LLM call with token budget check"""
        if not HAS_OLLAMA:
            return "LLM unavailable — Ollama not installed."

        # Token budget check
        if self.agent.state.tokens_used_session >= self.agent.state.session_budget * 0.98:
            lower_user = (user or "").lower()
            if any(cmd in lower_user for cmd in ["/new", "/reset", "fresh", "stats", "help", "/stats", "/wiki"]):
                pass
            else:
                return "Session token budget exceeded. Use /new to start a fresh session."

        tokens = self._count_tokens(system, user)
        self.agent.state.tokens_used_session += tokens
        self.agent.mark_dirty()

        model = model or CONFIG["default_model"]

        for attempt in range(3):
            try:
                resp = ollama.chat(model=model, messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ])
                return resp["message"]["content"].strip()
            except Exception as e:
                err = str(e).lower()
                if attempt < 2 and any(x in err for x in ["connection", "refused", "ollama", "timeout"]):
                    time.sleep(1.5 ** attempt)
                    continue
                if any(x in err for x in ["connection", "refused", "ollama"]):
                    return "[OLLAMA OFFLINE] — make sure 'ollama serve' is running"
                return f"[LLM ERROR] {e}"
        return "[LLM ERROR] Max retries exceeded"

    def call_llm_safe(self, system: str, user: str, model: Optional[str] = None):
        """Safe wrapper with failover models and Wiki context injection when appropriate."""
        # Inject wiki awareness into system prompt when relevant
        if "wiki" in user.lower() or "obsidian" in user.lower() or "/wiki" in user:
            wiki_note = "\n\nYou have access to a living Obsidian vault wiki with compiled, linked knowledge. Use it when relevant as a supplement to other memory methods."
            system = system + wiki_note

        models = [model or CONFIG["default_model"]] + CONFIG.get("failover_models", [])
        for m in models:
            try:
                return self.call_llm(system, user, model=m)
            except Exception as e:
                print(f"[LLM FAILOVER] {m} failed: {e}")
                continue
        return "[ERROR] All LLM models failed."

    def generate(self, system: str, prompt: str, model: Optional[str] = None) -> str:
        """Main generate method used by core.py delegation and conversation.py"""
        return self.call_llm_safe(system, prompt, model)

    def parallel_llm_calls(self, calls: List[Tuple[str, str, Optional[str]]], max_workers: int = 4) -> List[str]:
        """Fixed parallel LLM calls"""
        results = [None] * len(calls)

        def _worker(idx: int, system: str, user: str, model: Optional[str]):
            with LLM_LOCK:
                results[idx] = self.call_llm_safe(system, user, model)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_worker, i, system, user, model)
                for i, (system, user, model) in enumerate(calls)
            ]
            concurrent.futures.wait(futures)

        return results

    def _count_tokens(self, system: str, user: str) -> int:
        """Token counting with fallback"""
        with TOKEN_COUNT_CACHE_LOCK:
            if HAS_TIKTOKEN and self._tokenizer is None:
                try:
                    import tiktoken
                    self._tokenizer = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    self._tokenizer = None

            if self._tokenizer:
                return len(self._tokenizer.encode(system + "\n" + user))
            # Fallback estimation
            return int(len(system + "\n" + user) * 0.28) + 50