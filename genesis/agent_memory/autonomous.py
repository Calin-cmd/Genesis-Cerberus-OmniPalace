"""
Genesis v5.6.9 Cerberus OmniPalace — AutonomousManager
Full autonomous behaviors: journaling, reflection, predictions, coherence, decay, nudges,
self-improvement, and Obsidian wiki self-healing loop.
Balanced journaling + trace parsing for atomic fact extraction.
"""

from __future__ import annotations
import time
import random
import json
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..config import CONFIG, RAG_MODEL, STORAGE_DIR, TOPICS_DIR, TRACE_DIR
from .core import AgentMemory
from ..utils import dump_trace
from .persistence import archive_session_to_hall_of_records   # === RESTORED VISION IMPORT ===


class AutonomousManager:
    """Full autonomous behaviors for Genesis v5.6.9 Cerberus OmniPalace with WikiManager integration."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent

    def _create_journal_entry(self, force: bool = False) -> str:
        """Create a useful human-readable journal entry with proper timestamps."""
        sess = self.agent.current_session
        turns_since = self.agent.turns_since_last_journal.get(sess, 0)
        
        # Manual /journal is more lenient
        if force and turns_since < 12:
            pass
        elif not force and turns_since < 20:
            return "Journal skipped — not enough new activity since last entry."

        recent = self.agent.sessions.get(sess, [])[-15:]
        if len(recent) < 4 and not force:
            return "Journal skipped — insufficient conversation."

        hist = "\n".join([f"User: {t.get('prompt','')} → Genesis: {t.get('response','')[:200]}" for t in recent])
        
        journal_prompt = f"""Create a clear, human-readable journal entry (120-200 words).
Include exact real-world timestamp. Summarize what happened in this session: important commands, tool usage, user requests, and outcomes.
Focus on facts and progress. Be concise but readable.

Current real-world time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}
History:
{hist}"""

        journal_text = self.agent.call_llm_safe(
            "You are writing a clear, factual session journal entry for the user to read.",
            journal_prompt,
            model=RAG_MODEL
        )

        # Light filter only for automatic journals
        if not force and ("harness" in journal_text.lower() or "vault" in journal_text.lower() or len(journal_text) < 60):
            self.agent.turns_since_last_journal[sess] = 0
            return "Journal skipped — content was repetitive."

        entry_id = self.agent.add(journal_text, topic="journal", importance=0.85, tags=["journal", "session_summary"])

        self.agent.turns_since_last_journal[sess] = 0
        self.agent.stats["journals_run"] = self.agent.stats.get("journals_run", 0) + 1
        self.agent.mark_dirty()

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n=== JOURNAL ENTRY CREATED (ID: {entry_id}) @ {timestamp} ===\n{journal_text}\n")

        # === RESTORED ORIGINAL VISION: Archive to Hall of Records on every journal ===
        try:
            archive_session_to_hall_of_records(self.agent, sess, journal_text)
        except Exception as e:
            print(f"[AUTONOMOUS] Hall of Records archive warning: {e}")

        return journal_text

    def _run_reflection(self, force: bool = False) -> str:
        """Run reflection cycle."""
        sess = self.agent.current_session
        recent = self.agent.sessions.get(sess, [])[-12:]
        if not recent and not force:
            return "No recent activity for reflection."

        hist = "\n".join([f"User: {t.get('prompt','')} → Genesis: {t.get('response','')[:180]}" for t in recent])
        
        reflection_prompt = f"""Reflect concisely on this conversation.
Focus on tool effectiveness, user needs, and what could be improved.
Be honest and constructive.

History:
{hist}"""

        reflection = self.agent.call_llm_safe(
            "You are performing concise, useful self-reflection.",
            reflection_prompt,
            model=RAG_MODEL
        )

        self.agent.add(reflection, topic="reflection", importance=0.82, tags=["self_improvement"])
        self.agent.stats["reflections_run"] = self.agent.stats.get("reflections_run", 0) + 1
        self.agent.mark_dirty()

        print(f"\n=== REFLECTION @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n{reflection[:600]}...\n")
        return reflection

    def generate_forward_predictions(self, force: bool = False) -> str:
        """Generate 3 actionable forward predictions."""
        sess = self.agent.current_session
        recent = self.agent.sessions.get(sess, [])[-10:]
        if not recent and not force:
            return "Not enough context for predictions."

        hist = "\n".join([f"User: {t.get('prompt','')} → Genesis: {t.get('response','')[:150]}" for t in recent])
        
        pred_prompt = f"""Based strictly on the conversation history,
generate 3 short, actionable predictions about what the user might need next.
Keep them practical.

History:
{hist}"""

        predictions = self.agent.call_llm_safe(
            "You are generating forward predictions as Genesis.",
            pred_prompt,
            model=RAG_MODEL
        )

        self.agent.add(predictions, topic="forward_pred", importance=0.82, tags=["prediction"])
        self.agent.stats["predictions_run"] = self.agent.stats.get("predictions_run", 0) + 1
        self.agent.mark_dirty()

        print(f"\n=== FORWARD PREDICTIONS @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n{predictions}\n")
        return predictions

    def run_coherence_check(self) -> str:
        """Run coherence analysis."""
        sess = self.agent.current_session
        recent = self.agent.sessions.get(sess, [])[-12:]
        hist = "\n".join([f"User: {t.get('prompt','')} → Genesis: {t.get('response','')[:200]}" for t in recent])
        
        coherence_prompt = f"""Analyze the coherence of this conversation history.
Rate overall coherence (0-100%). Suggest one small improvement.

History:
{hist}"""

        result = self.agent.call_llm_safe(
            "You are performing a coherence check.",
            coherence_prompt,
            model=RAG_MODEL
        )

        self._process_coherence_result(result)
        return result

    def _process_coherence_result(self, result: str):
        self.agent.add(result, topic="coherence", importance=0.85, tags=["consistency"])
        self.agent.stats["coherences_run"] = self.agent.stats.get("coherences_run", 0) + 1
        self.agent.mark_dirty()

    def _decay_importance(self):
        try:
            if hasattr(self.agent.index, 'update_importance'):
                for entry_id in list(self.agent.index.index_lines)[:120]:
                    try:
                        match = re.search(r'id=([a-z0-9]+)', entry_id)
                        if match:
                            self.agent.index.update_importance(entry_id=match.group(1), delta=-0.04)
                    except:
                        pass
            print(f"[DECAY] Importance decay applied to recent entries @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"[DECAY] Warning: Decay failed - {e}")
        
        self.agent.stats["decays_run"] = self.agent.stats.get("decays_run", 0) + 1
        self.agent.mark_dirty()

    def run_autonomous_nudge(self):
        nudge_prompt = """Generate a short, proactive, and useful nudge for the user."""

        nudge = self.agent.call_llm_safe(
            "You are generating an autonomous nudge.",
            nudge_prompt,
            model=RAG_MODEL
        )

        self.agent.add(nudge, topic="nudge", importance=0.75, tags=["proactive"])
        print(f"\n[AUTONOMOUS NUDGE @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {nudge[:220]}...\n")
        self.agent.mark_dirty()

    def run_self_improvement_cycle(self) -> str:
        """Improved cycle: rotates through multiple behaviors."""
        print(f"[SELF-IMPROVEMENT] Starting balanced cycle @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        
        self._run_reflection(force=True)
        self.generate_forward_predictions(force=True)
        self.run_coherence_check()
        
        # Occasional journal during self-improvement
        if random.random() < 0.4:
            self._create_journal_entry(force=True)

        self.agent.stats["improvement_cycles"] = self.agent.stats.get("improvement_cycles", 0) + 1
        self.agent.mark_dirty()
        return "✅ Self-improvement cycle completed (reflection + predictions + coherence + occasional journal)."

    def _parse_traces_for_atomic_facts(self):
        """Parse recent traces and extract atomic facts for memory indexing."""
        today = datetime.now().strftime('%Y%m%d')
        trace_file = TRACE_DIR / f"{today}.jsonl"
        
        if not trace_file.exists():
            return

        try:
            lines = trace_file.read_text(encoding="utf-8").splitlines()[-80:]
            for line in lines:
                if not line.strip():
                    continue
                try:
                    trace = json.loads(line)
                    if trace.get("event_type") == "llm_thought":
                        fact = f"Internal thought: {trace.get('reasoning', '')} | Stage: {trace.get('stage', '')} | Tools: {trace.get('tools_used', False)}"
                        self.agent.add(
                            fact,
                            topic="atomic_trace_fact",
                            importance=0.78,
                            tags=["internal_reasoning", "trace", "atomic_fact"]
                        )
                except:
                    continue
        except Exception as e:
            print(f"[TRACE PARSER] Error: {e}")

    def _run_full_auto_dream(self):
        """Full AutoDream cycle with trace parsing and reduced journal frequency."""
        print(f"[AUTODREAM] Starting full maintenance cycle @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        
        self._parse_traces_for_atomic_facts()
        self._decay_importance()
        self.run_self_improvement_cycle()
        
        # Light journal at end of dream
        if random.random() < 0.6:
            self._create_journal_entry(force=False)
        
        print(f"[AUTODREAM] Cycle completed @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.agent.mark_dirty()

    def run_daemons(self):
        """Run one cycle of all autonomous daemons."""
        if not CONFIG.get("self_nudging_enabled", True):
            return
        try:
            self._run_full_auto_dream()
        except Exception as e:
            print(f"[AUTONOMOUS] Daemon cycle error: {e}")

    def start_background_daemons(self):
        """Start background thread for autonomous behaviors."""
        import threading
        def daemon_loop():
            while True:
                try:
                    time.sleep(180)  # Every 3 minutes
                    if random.random() < 0.7:   # Probabilistic to avoid overload
                        self.run_daemons()
                except Exception:
                    time.sleep(60)
        
        thread = threading.Thread(target=daemon_loop, daemon=True)
        thread.start()
        print("[AUTONOMOUS] Background daemons started (journaling, reflection, Hall of Records archiving active)")