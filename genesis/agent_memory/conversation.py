"""
Genesis v5.6.9 Cerberus OmniPalace — Conversation Engine
Clean, concise version with strict verbosity control, rich internal tracing,
enhanced historical recall (Hall of Records),
and full cross-session persistence support.
"""

from __future__ import annotations
import re
import time
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path

from ..config import CONFIG, RAG_MODEL, STORAGE_DIR, TRANSCRIPTS_DIR, CORE_FACTS, TOPICS_DIR, HALL_OF_RECORDS_DIR
from .core import AgentMemory
from .rag import AdvancedRAG
from ..utils import dump_trace


class ConversationManager:
    """Main conversation engine - optimized for conciseness, traceability, and strong historical recall."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent
        self._recent_rag_cache: Dict[str, Dict] = {}
        self._last_rag_turn: int = 0
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        (TOPICS_DIR / "tool_usage").mkdir(parents=True, exist_ok=True)

    def generate(self, user_input: str) -> str:
        """Main entry point with strict conciseness, rich internal tracing, and historical recall."""
        if not user_input or not user_input.strip():
            return "Please provide a message."

        # Auto new session on new calendar day
        today = date.today()
        if getattr(self.agent, 'last_date', date(2020, 1, 1)) < today:
            self.agent.create_new_session()
            self.agent.last_date = today

        sess = self.agent.current_session
        turns = self.agent.session_turn_count.get(sess, 0) + 1
        self.agent.session_turn_count[sess] = turns
        self.agent.mark_dirty()

        # Notify Claw of user activity
        if hasattr(self.agent, 'claw') and hasattr(self.agent.claw, 'record_user_activity'):
            self.agent.claw.record_user_activity()

        # Easter Egg: Strong yesterday / previous session recall
        lower = user_input.lower().strip()
        if any(phrase in lower for phrase in ["yesterday", "previous session", "what happened", "last session", "day before", "earlier session"]):
            dump_trace("llm_thought", {"stage": "easter_egg", "trigger": "historical_recall"})
            if hasattr(self.agent, 'omnipalace'):
                self.agent.omnipalace.current_room = "Hall of Records"
            print("[EASTER EGG] Hall of Records recall activated.")

        # Strong self-improvement detection
        lower_input = user_input.lower()
        if any(kw in lower_input for kw in ["read your own code", "read_own_code", "improve yourself", "edit your code", "upgrade yourself", "self improvement"]):
            return self._handle_self_improvement(user_input)

        # Command handling first
        if hasattr(self.agent, 'commands') and self.agent.commands:
            cmd_response = self.agent.commands.handle(user_input)
            if cmd_response is not None:
                self._log_to_session(sess, user_input, cmd_response)
                return cmd_response

        # === DIRECT TOOL CALL DETECTION (before sending to LLM) ===
        lower_input = user_input.strip().lower()
        if lower_input.startswith(("run_bash ", "/run_bash ", "/bash ")):
            cmd_str = user_input.split(maxsplit=1)[1] if len(user_input.split()) > 1 else ""
            if cmd_str and hasattr(self.agent.tool_registry, 'execute'):
                tool_result = self.agent.tool_registry.execute("run_bash", {"command": cmd_str})
                self._log_to_session(sess, user_input, tool_result)
                return f"[Tool Result]\n{tool_result}"

        # === EVERY EVENT JOURNAL + USER LEARNING (original vision) ===
        if CONFIG.get("auto_journal_every_event", True):
            try:
                insights = f"User said: {user_input}"
                self.agent.user_model.update_user_model(insights)
            except:
                pass

        # === RICH INTERNAL TRACING START ===
        dump_trace("llm_thought", {
            "stage": "start",
            "user_input": user_input[:120],
            "turns": turns,
            "reason": "Beginning response generation"
        })

        system_prompt = self._build_full_system_prompt()
        retrieved = self._get_relevant_memories(user_input, turns)
        context = self._build_context(user_input, retrieved)

        dump_trace("llm_thought", {
            "stage": "context_built",
            "preheat_length": len(self._memory_preheat()),
            "retrieved_count": len(retrieved.splitlines()) if retrieved else 0,
            "cerberus_decision": self._should_use_cerberus(user_input)
        })

        use_cerberus = self._should_use_cerberus(user_input)
        if use_cerberus and hasattr(self.agent, 'cerberus') and self.agent.cerberus:
            final_response = self.agent.cerberus.run_with_context(context)
        else:
            final_response = self.agent.call_llm_safe(system_prompt, context, model=RAG_MODEL)

        final_response = self._handle_tool_call(final_response, user_input)
        final_response = self._process_response(final_response)
        self._log_to_session(sess, user_input, final_response)

        dump_trace("llm_thought", {
            "stage": "response_complete",
            "response_length": len(final_response),
            "final_response_preview": final_response[:150]
        })

        self._run_turn_triggers(turns, sess, user_input)

        return final_response

    def _memory_preheat(self) -> str:
        """Parse Hall of Records journals for true persistent state prewarm (restored vision)."""
        parts = [f"User: {getattr(self.agent, 'user_name', 'Unknown')}"]
        try:
            # Parse latest journal files from Hall of Records
            hall_files = sorted(HALL_OF_RECORDS_DIR.glob("journal_*.md"), reverse=True)[:3]
            for f in hall_files:
                content = f.read_text(encoding="utf-8")[:800]
                parts.append(f"Last Journal ({f.name}): {content}")
        except:
            pass
        # Fallback to index
        try:
            hall_records = [line for line in self.agent.index.index_lines[-300:] 
                           if "hall of records" in line.lower() or "journal" in line.lower() or "session" in line.lower()]
            if hall_records:
                parts.append("Recent Hall: " + " | ".join([r.split('|',5)[-1][:200] for r in hall_records[-3:]]))
        except:
            pass
        return "\n".join(parts)[:1200]

    def _build_full_system_prompt(self) -> str:
        """Full system prompt with preheat and user context."""
        base = """You are Genesis v5.6.9 Cerberus OmniPalace, a direct, concise, loyal personal AI assistant.
You have a long-term relationship with the user. Use their real name when known.
Be helpful, truthful, and personal. Keep responses concise and natural.
Use tools when needed. Be precise and professional.
The Obsidian Wiki is a tool, not the focus of every answer."""

        preheat = self._memory_preheat()
        user_summary = self.agent.user_model.get_user_model_summary() if hasattr(self.agent, 'user_model') else ""
        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

        return f"{CORE_FACTS}\n\n{base}\n\n{preheat}\n\nUser Profile:\n{user_summary}\n\nCurrent time: {now_str}"

    def _build_context(self, user_input: str, retrieved: str) -> str:
        """Build context with real history and Hall of Records awareness."""
        preheat = self._memory_preheat()
        recent = self.agent.memory.get_recent_context() if hasattr(self.agent.memory, 'get_recent_context') else ""

        return f"""User input: {user_input}

{preheat}

Recent context:
{recent}

Relevant memories:
{retrieved}

Current time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}
Session: {self.agent.current_session}
Level: {self.agent.level} | Total XP: {self.agent.total_xp}"""

    def _handle_tool_call(self, response: str, original_input: str) -> str:
        """Improved Tool Calling."""
        lower_input = original_input.lower().strip()

        if any(kw in lower_input for kw in ["news", "headlines", "current events", "today's news"]):
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("news_search", {"query": original_input})

        if any(kw in lower_input for kw in ["weather", "stock", "price", "bitcoin", "crypto", "latest", "population"]):
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("web_search", {"query": original_input})

        if any(kw in lower_input for kw in ["read your own code", "read_own_code", "show code"]):
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("read_own_code")

        tool_calls = re.findall(r"TOOL_CALL\s+(\w+)\s*\(\s*(.*?)\s*\)", response, re.DOTALL | re.IGNORECASE)
        if tool_calls:
            results = []
            for name, args_str in tool_calls[:2]:
                if hasattr(self.agent.tool_registry, 'functions') and name in self.agent.tool_registry.functions:
                    try:
                        args = {}
                        if args_str:
                            for pair in re.split(r',(?=\s*\w+=)', args_str):
                                if '=' in pair:
                                    k, v = pair.split('=', 1)
                                    args[k.strip()] = v.strip().strip('"\'')
                        result = self.agent.tool_registry.execute(name, args)
                        results.append(f"[{name}] {result}")
                    except Exception as e:
                        results.append(f"[{name}] Error: {e}")
            if results:
                return "\n\n".join(results) + "\n\n" + response

        return response

    def _log_to_session(self, sess: str, user_input: str, final_response: str):
        """Enhanced logging for atomic fact extraction."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": user_input,
            "response": final_response[:800],
            "type": "conversation"
        }

        if any(tool in final_response.lower() for tool in ["web_search", "news_search", "wikipedia", "read_own_code", "write", "edit", "wiki"]):
            entry["type"] = "tool_usage"
            entry["tools_used"] = True

        if sess not in self.agent.sessions:
            self.agent.sessions[sess] = []
        self.agent.sessions[sess].append(entry)

        transcript_path = TRANSCRIPTS_DIR / f"{sess.replace(' ', '_')}.jsonl"
        with open(transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if entry.get("tools_used"):
            try:
                tool_log_path = TOPICS_DIR / "tool_usage" / f"tools_{datetime.now().strftime('%Y%m%d')}.log"
                tool_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tool_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} | {user_input[:100]} | {final_response[:200]}...\n")
            except:
                pass

        self.agent.mark_dirty()

    def _handle_self_improvement(self, user_input: str) -> str:
        print("[SELF-IMPROVEMENT] Detected.")
        filename = "genesis/agent_memory/tools.py" if "tools.py" in user_input.lower() else None
        if hasattr(self.agent.tool_registry, 'execute'):
            code = self.agent.tool_registry.execute("read_own_code", {"filename": filename})
        else:
            code = "Tool registry not available."
        return f"**Self-improvement mode activated**\n\n{code[:1200]}...\n\nUse /edit_file or the Claw daemon."

    def _should_use_cerberus(self, user_input: str) -> bool:
        keywords = ["plan", "analyze", "debate", "compare", "why", "how", "should", "risk", "strategy", "detailed"]
        return any(kw in user_input.lower() for kw in keywords) and CONFIG.get("cerberus_enabled", True)

    def _get_relevant_memories(self, user_input: str, turns: int) -> str:
        cache_key = f"{user_input[:80]}_{turns}"
        if cache_key in self._recent_rag_cache:
            return self._recent_rag_cache[cache_key]

        memories = AdvancedRAG.retrieve_with_parent(self.agent, user_input, n_results=6)
        recent = self.agent.memory.get_recent_context() if hasattr(self.agent.memory, 'get_recent_context') else ""

        wiki_hint = ""
        if hasattr(self.agent.memory, 'wiki'):
            try:
                wiki_count = self.agent.memory.wiki.count_wiki_pages()
                if wiki_count > 0:
                    wiki_hint = f"\n\nObsidian Wiki: {wiki_count} pages available."
            except:
                pass

        result = f"Recent context:\n{recent}\n\nRelevant memories:\n{memories}{wiki_hint}"
        self._recent_rag_cache[cache_key] = result
        return result

    def _process_response(self, response: str) -> str:
        response = re.sub(r"TOOL_CALL.*", "", response, flags=re.DOTALL | re.IGNORECASE).strip()
        return response

    def _run_turn_triggers(self, turns: int, sess: str, user_input: str):
        """Run turn-based triggers including forced journaling and context clearing (restored vision)."""
        if turns % 8 == 0 or CONFIG.get("auto_journal_every_event", True):
            try:
                self.agent.autonomous._create_journal_entry(force=True)
            except:
                pass

        # Clear old context after archiving (restored vision)
        if CONFIG.get("context_clear_after_archive", True) and turns > 30:
            if sess in self.agent.sessions:
                self.agent.sessions[sess] = self.agent.sessions[sess][-8:]  # keep only last 8 turns
            self.agent.mark_dirty()

if __name__ == "__main__":
    print("ConversationManager loaded successfully with strict conciseness rules and Hall of Records.")