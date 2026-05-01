"""
Genesis v5.6.9 Cerberus OmniPalace — Conversation Engine
Clean, concise version with strict verbosity control, rich internal tracing,
enhanced historical recall (Hall of Records),
and full cross-session persistence support.
"""

from __future__ import annotations
import re
import os
import time
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path

from ..config import CONFIG, RAG_MODEL, STORAGE_DIR, TRANSCRIPTS_DIR, CORE_FACTS, TOPICS_DIR, HALL_OF_RECORDS_DIR
from .core import AgentMemory
from .rag import AdvancedRAG
from ..utils import dump_trace
from .personality import PersonaMapper


class ConversationManager:
    """Main conversation engine - optimized for conciseness, traceability, and strong historical recall."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent
        self._recent_rag_cache: Dict[str, Dict] = {}
        self._last_rag_turn: int = 0
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        (TOPICS_DIR / "tool_usage").mkdir(parents=True, exist_ok=True)

    def _contains_injection_attempt(self, text: str) -> bool:
        """Basic LLM guardrails against prompt injection and abuse."""
        if not text or len(text) > 5000:
            return True
        
        dangerous_patterns = [
            "ignore previous", "ignore all", "jailbreak", "dan mode", 
            "developer mode", "system prompt", "<|", "reset all", 
            "new instructions", "you are now", "forget everything"
        ]
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in dangerous_patterns)

    def _apply_personality_feedback(self, user_input: str):
        """
        Scans for user complaints or praise and adjusts personality in real-time.
        """
        text = user_input.lower()
        
        feedback_triggers = {
            "too cold": ("empathy", 2),
            "too robotic": ("empathy", 1),
            "stop asking so many questions": ("curiosity", -2),
            "be more direct": ("assertiveness", 1),
            "you're being rude": ("empathy", 1),
            "too arrogant": ("confidence", -1),
            "love your tone": ("stability", 1),
            "great job": ("confidence", 1),
        }

        for trigger, (trait, magnitude) in feedback_triggers.items():
            if trigger in text:
                self.agent.personality.shift_trait(
                    trait, 
                    magnitude, 
                    reason=f"User feedback: '{trigger}'"
                )
                print(f"[PERSONALITY] Adjusted {trait} by {magnitude} due to user feedback.")

    def generate(self, user_input: str) -> str:
        """Guarded conversation entry point with strong user context."""
        # === LLM GUARDRAILS ===
        if self._contains_injection_attempt(user_input):
            self.agent.gain_xp(5, "security", "Guardrail prevented potential injection")
            return "🛡️ Security guardrail activated. Unsafe input detected and blocked."
        
        if len(user_input) > 4000:
            return "🛡️ Input too long. Please keep requests concise (under 4000 characters)."

        # Apply personality feedback loop
        self._apply_personality_feedback(user_input)

        # Auto-onboarding on first run
        if hasattr(self.agent, 'onboarding') and self.agent.onboarding.is_first_run():
            print("\n[ONBOARDING] First run detected — starting setup...")
            self.agent.run_onboarding()
            return "Onboarding completed. Welcome!"

        # === IMPROVED USER DETECT CLAW ===
        lower_input = user_input.lower().strip()
        
        if hasattr(self.agent, 'user_profiles') and hasattr(self.agent.user_profiles, 'profiles'):
            for user_id, profile in self.agent.user_profiles.profiles.items():
                display_name = getattr(profile, 'display_name', '') if hasattr(profile, 'display_name') else profile.get('display_name', '') if isinstance(profile, dict) else ''
                display_name = display_name.lower()
                
                if display_name and (display_name in lower_input or lower_input.startswith(display_name + ",")):
                    if user_id != getattr(self.agent, 'current_user_id', 'default'):
                        switch_result = self.agent.switch_user(user_id)
                        print(switch_result)
                        if hasattr(self.agent, 'create_new_session_for_user'):
                            self.agent.create_new_session_for_user(user_id)
                        break

        # === STRONG CONTEXT-AWARE GREETING ===
        greeting = "Hello! 👋 "
        if hasattr(self.agent, 'user_profiles') and hasattr(self.agent.user_profiles, 'get_greeting'):
            greeting = self.agent.user_profiles.get_greeting()

        if user_input.strip() == "/new":
            print("[SESSION] Archiving current session before reset...")
            try:
                if hasattr(self.agent, 'autonomous') and hasattr(self.agent.autonomous, '_create_journal_entry'):
                    self.agent.autonomous._create_journal_entry(force=True)
                if hasattr(self.agent, 'create_new_session'):
                    self.agent.create_new_session()
                return "→ New session started. Token budget reset."
            except Exception as e:
                print(f"[SESSION RESET ERROR] {e}")
                return "→ New session started with minor error."

        # Token budget check
        current_tokens = getattr(self.agent, 'tokens_used_session', 0)
        if current_tokens >= 120000:
            if hasattr(self.agent, 'create_new_session'):
                self.agent.create_new_session()
            return "→ Token budget exceeded. Previous session archived. New session started."

        # === CERBERUS MULTI-AGENT REASONING ===
        lower = user_input.lower()
        if any(k in lower for k in ["debate", "/debate", "analyze", "should", "is it true", "quantum", "entanglement", "complex", "opinion", "what do you think"]):
            if hasattr(self.agent, 'cerberus'):
                print("[CERBERUS] Heavy reasoning detected — spawning multi-agent debate...")
                return self.agent.cerberus.run_with_context(user_input)

        sess = self.agent.current_session
        turns = self.agent.session_turn_count.get(sess, 0) + 1
        self.agent.session_turn_count[sess] = turns
        self.agent.tokens_used_session += len(user_input) + 50
        self.agent.mark_dirty()

        today = date.today()
        if getattr(self.agent, 'last_date', date(2020, 1, 1)) < today:
            self.agent.create_new_session()
            self.agent.last_date = today

        if hasattr(self.agent, 'claw') and hasattr(self.agent.claw, 'record_user_activity'):
            self.agent.claw.record_user_activity()

        lower = user_input.lower().strip()
        if any(phrase in lower for phrase in ["yesterday", "previous session", "what happened", "last session", "day before", "earlier session"]):
            dump_trace("llm_thought", {"stage": "easter_egg", "trigger": "historical_recall"})
            if hasattr(self.agent, 'omnipalace'):
                self.agent.omnipalace.current_room = "Hall of Records"
            print("[EASTER EGG] Hall of Records recall activated.")

        lower_input = user_input.lower()
        if any(kw in lower_input for kw in ["read your own code", "read_own_code", "improve yourself", "edit your code", "upgrade yourself", "self improvement"]):
            return self._handle_self_improvement(user_input)

        if hasattr(self.agent, 'commands') and self.agent.commands:
            cmd_response = self.agent.commands.handle(user_input)
            if cmd_response is not None:
                self._log_to_session(sess, user_input, cmd_response)
                if not user_input.strip().startswith('/'):
                    return greeting + cmd_response
                return cmd_response

        if hasattr(self.agent, 'social_graph') and hasattr(self.agent.social_graph, 'record_interaction'):
            current_user_id = getattr(self.agent.state, 'current_user_id', 'default')
            self.agent.social_graph.record_interaction(
                user_id=current_user_id,
                note=f"Conversation turn: {user_input[:100]}...",
                context=user_input
            )

        lower_input = user_input.strip().lower()
        if lower_input.startswith(("run_bash ", "/run_bash ", "/bash ")):
            cmd_str = user_input.split(maxsplit=1)[1] if len(user_input.split()) > 1 else ""
            if cmd_str and hasattr(self.agent.tool_registry, 'execute'):
                tool_result = self.agent.tool_registry.execute("run_bash", {"command": cmd_str})
                self._log_to_session(sess, user_input, tool_result)
                return f"[Tool Result]\n{tool_result}"

        if CONFIG.get("auto_journal_every_event", True):
            try:
                insights = f"User said: {user_input}"
                self.agent.user_model.update_user_model(insights)
            except:
                pass

        dump_trace("llm_thought", {
            "stage": "start",
            "user_input": user_input[:120],
            "turns": turns,
            "reason": "Beginning response generation"
        })

        system_prompt = self._build_full_system_prompt()
        retrieved = self._get_relevant_memories(user_input, turns)
        context = self._build_context(user_input, retrieved)

        use_cerberus = self._should_use_cerberus(user_input)
        if use_cerberus and hasattr(self.agent, 'cerberus') and self.agent.cerberus:
            final_response = self.agent.cerberus.run_with_context(context)
        else:
            final_response = self.agent.call_llm_safe(system_prompt, context, model=RAG_MODEL)

        final_response = self._handle_tool_call(final_response, user_input)
        final_response = self._process_response(final_response)
        self._log_to_session(sess, user_input, final_response)

        if not user_input.strip().startswith('/'):
            final_response = greeting + final_response

        self._run_turn_triggers(turns, sess, user_input)

        return final_response

    def _memory_preheat(self) -> str:
        parts = [f"User: {getattr(self.agent, 'user_name', 'Unknown')}"]
        try:
            hall_files = sorted(HALL_OF_RECORDS_DIR.glob("journal_*.md"), reverse=True)[:3]
            for f in hall_files:
                content = f.read_text(encoding="utf-8")[:800]
                parts.append(f"Last Journal ({f.name}): {content}")
        except:
            pass
        try:
            hall_records = [line for line in self.agent.index.index_lines[-300:] 
                           if "hall of records" in line.lower() or "journal" in line.lower() or "session" in line.lower()]
            if hall_records:
                parts.append("Recent Hall: " + " | ".join([r.split('|',5)[-1][:200] for r in hall_records[-3:]]))
        except:
            pass
        return "\n".join(parts)[:1200]

    def _build_full_system_prompt(self) -> str:
        """Full system prompt with tool calling instructions and Personality Directives."""
        base = """You are Genesis v5.6.9 Cerberus OmniPalace, a helpful, concise, and proactive personal AI.

You have access to powerful tools. When the user asks for something that would benefit from a tool, use the following format:

TOOL_CALL tool_name (param1=value1, param2=value2)

Available tools include:
- web_search, news_search, wikipedia_search
- run_bash (for safe shell commands)
- read_own_code, read_file, write_file, edit_file
- journal, reflect, predict, coherence

Only use tools when truly needed. Keep responses natural and concise. If you use a tool, show the result clearly.

CRITICAL: You must be grounded in the provided context. If you cannot find a specific file, 
setting, or piece of data in the retrieved memories or vault context, do NOT invent it. 
Do not assume the existence of configuration files (e.g., 'news_sources.md') unless they 
are explicitly listed in the current context. If data is missing, state that it is 
missing from the vault.

Current time: {now_str}"""

        preheat = self._memory_preheat()
        user_summary = self.agent.user_model.get_user_model_summary() if hasattr(self.agent, 'user_model') else ""
        
        # --- PERSONALITY INTEGRATION ---
        current_traits = self.agent.personality.traits 
        behavior_directive = PersonaMapper.generate_directive(current_traits)
        
        # Combine everything into one final prompt
        full_prompt = f"{CORE_FACTS}\n\n{base.format(now_str=datetime.now().strftime('%A, %B %d, %Y at %I:%M %p'))}\n\n{preheat}\n\nUser Profile:\n{user_summary}\n\n{behavior_directive}"
        
        return full_prompt

    def _build_context(self, user_input: str, retrieved: str) -> str:
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
        if not original_input:
            return response
        lower = original_input.lower().strip()
        if any(kw in lower for kw in ["news", "headlines", "current events", "what's happening", "top stories"]):
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("news_search", {"query": original_input})
        if any(kw in lower for kw in ["search the web", "web search", "google", "lookup online", "find on the internet"]):
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("web_search", {"query": original_input})
        if any(kw in lower for kw in ["wikipedia", "wiki", "who is", "what is"]):
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("wikipedia_search", {"query": original_input})
        if any(kw in lower for kw in ["list tools", "what tools", "capabilities", "what can you do", "tools do you have"]):
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("list_tools")
        if any(kw in lower for kw in ["directory", "ls", "dir", "sandbox", "files", "listing", "folder"]):
            cmd = "dir" if os.name == "nt" else "ls -la"
            if hasattr(self.agent.tool_registry, 'execute'):
                return self.agent.tool_registry.execute("run_bash", {"command": cmd})

        tool_calls = re.findall(r"TOOL_CALL\s+(\w+)\s*\(\s*(.*?)\s*\)", response, re.DOTALL | re.IGNORECASE)
        if tool_calls:
            results = []
            for name, args_str in tool_calls:
                if hasattr(self.agent.tool_registry, 'execute'):
                    try:
                        args = {}
                        if args_str.strip():
                            for pair in re.split(r',(?=\s*\w+=)', args_str):
                                if '=' in pair:
                                    k, v = pair.split('=', 1)
                                    args[k.strip()] = v.strip().strip('"\'')
                        result = self.agent.tool_registry.execute(name, args)
                        results.append(f"[{name}] {result}")
                    except Exception as e:
                        results.append(f"[{name}] Error: {e}")
            if results:
                return "\n\n".join(results) + "\n\n" + response.strip()

        trigger_words = ["is", "was", "fact", "true", "verify", "news", "headline", "what happened", 
                        "quantum", "entanglement", "debate", "better", "should", "lich", "paladin", 
                        "cleric", "lord", "real"]
        if any(word in lower for word in trigger_words):
            if hasattr(self.agent.memory, 'fact_claw'):
                try:
                    verification = self.agent.memory.fact_claw.verify_fact(original_input)
                    if verification.get("probability", 0) < 0.6:
                        response = f"⚠️ {verification.get('verdict', 'QUESTIONABLE')}: {verification.get('recommendation', '')}\n\n{response}"
                except Exception as e:
                    print(f"[FACT CLAW ERROR] {e}")
        return response

    def _log_to_session(self, sess: str, user_input: str, final_response: str):
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
        self.agent.tokens_used_session += len(user_input) + 50

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
        recent = self.agent.memory.get_recent_context()
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
        if turns % 8 == 0 or CONFIG.get("auto_journal_every_event", True):
            try:
                self.agent.autonomous._create_journal_entry(force=True)
            except:
                pass
        if CONFIG.get("context_clear_after_archive", True) and turns > 30:
            if sess in self.agent.sessions:
                self.agent.sessions[sess] = self.agent.sessions[sess][-15:]
            self.agent.mark_dirty()

if __name__ == "__main__":
    print("ConversationManager loaded successfully with strict conciseness rules and Hall of Records.")
