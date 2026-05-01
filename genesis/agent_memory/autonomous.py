"""
Genesis v5.6.9 Cerberus OmniPalace — AutonomousManager
Full autonomous behaviors: journaling, reflection, predictions, coherence, decay, nudges,
self-improvement, and Obsidian wiki self-healing loop.
"""

from __future__ import annotations
import time
import random
import json
import re
from datetime import datetime
from typing import Optional
from pathlib import Path
from .claw_safety import ClawSafety

from ..config import CONFIG, RAG_MODEL, STORAGE_DIR, TOPICS_DIR, TRACE_DIR
from .core import AgentMemory
from ..utils import dump_trace
from .persistence import archive_session_to_hall_of_records


class AutonomousManager:
    """Full autonomous behaviors for Genesis v5.6.9 Cerberus OmniPalace."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent
        self.repo_root = Path(__file__).parent.parent.parent.resolve()
        
        try:
            self.claw_safety = ClawSafety(self.repo_root)
            print("[CLAW] SelfImprovementDaemon integrated with safety layer")
        except Exception as e:
            print(f"[CLAW INIT WARNING] {e}")
            self.claw_safety = None

        # === RATE-LIMIT GUARDS ===
        self._last_cycle = time.time() - 181   # first run allowed immediately
        self._last_journal = time.time() - 301
        self._last_cycle = time.time() + 180 # 3-min cooldown (but *signal strength* matters)

    def _create_journal_entry(self, force: bool = False) -> str:
        """Create a useful human-readable journal entry from Genesis's point of view."""
        sess = self.agent.current_session
        turns_since = self.agent.turns_since_last_journal.get(sess, 0)
        
        # Rate limit protection
        if not force and (time.time() - self._last_journal < 300):
            return "Journal skipped — rate limited (300s cooldown)."

        if not force and turns_since < 20:
            return "Journal skipped — not enough new activity since last entry."

        recent = self.agent.sessions.get(sess, [])[-15:]
        if len(recent) < 4 and not force:
            return "Journal skipped — insufficient conversation."

        # Get current active user safely
        current_user_name = getattr(self.agent, 'current_user', None)
        current_user_name = current_user_name.display_name if current_user_name else "the active user"

        hist = "\n".join([f"User ({current_user_name}): {t.get('prompt','')} → Genesis: {t.get('response','')[:200]}" 
                         for t in recent])
        
        journal_prompt = f"""You are Genesis. Write a clear, first-person journal entry (120-160 words) about this session.

Current active user: {current_user_name}
Real-world time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}

Recent conversation:
{hist}

Guidelines:
- Write strictly from your own perspective ("I", "me", "my")
- Be factual, concise, and natural
- Mention important context, user interactions, and your internal state
- Do not use third-person language
- Do not refer to yourself as "Genesis" in the entry body
- End with a short forward-looking note if appropriate"""

        journal_text = self.agent.call_llm_safe(
            "You are writing a personal, first-person session journal as Genesis.",
            journal_prompt,
            model=RAG_MODEL
        )

        # CRITICAL: suppress_daemons=True prevents re-triggering the router
        entry_id = self.agent.add(journal_text, topic="journal", importance=0.85, tags=["journal", "session_summary"], suppress_daemons=True)

        self.agent.turns_since_last_journal[sess] = 0
        self.agent.stats["journals_run"] = self.agent.stats.get("journals_run", 0) + 1
        self.agent.mark_dirty()

        self._last_journal = time.time()

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n=== JOURNAL ENTRY CREATED (ID: {entry_id}) @ {timestamp} ===\n{journal_text}\n")

        try:
            archive_session_to_hall_of_records(self.agent, sess, journal_text)
        except Exception as e:
            print(f"[AUTONOMOUS] Hall of Records warning: {e}")

        return journal_text

    def _run_reflection(self, force: bool = False) -> str:
        """Run reflection cycle."""
        if not force and (time.time() - self._last_cycle < 30):
            return "Reflection skipped — rate limited."

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

        # suppress_daemons=True
        self.agent.add(reflection, topic="reflection", importance=0.82, tags=["self_improvement"], suppress_daemons=True)
        self.agent.stats["reflections_run"] = self.agent.stats.get("reflections_run", 0) + 1
        self.agent.mark_dirty()

        print(f"\n=== REFLECTION @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n{reflection[:600]}...\n")
        return reflection

    def generate_forward_predictions(self, force: bool = False) -> str:
        """Generate 3 actionable forward predictions."""
        if not force and (time.time() - self._last_cycle < 45):
            return "Predictions skipped — rate limited."

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

        # suppress_daemons=True
        self.agent.add(predictions, topic="forward_pred", importance=0.82, tags=["prediction"], suppress_daemons=True)
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
        """Improved cycle with Claw Safety Layer — robust version."""
        if time.time() - self._last_cycle < 120:   # 2 minutes minimum between full cycles
            return "Improvement cycle skipped — rate limited."

        print(f"[SELF-IMPROVEMENT] Starting balanced cycle @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        
        self._run_reflection(force=True)
        self.generate_forward_predictions(force=True)
        self.run_coherence_check()
        
        if random.random() < 0.4:
            self._create_journal_entry(force=True)

        # === CLAW SAFETY (unchanged) ===
        try:
            if hasattr(self, 'claw_safety') and self.claw_safety is not None:
                suggestion = self._generate_claw_improvement_suggestion()
                review_result = self.claw_safety.review_and_apply_patch(
                    patch_content=suggestion,
                    description=f"Self-improvement cycle"
                )
                print(review_result)
            else:
                print("[CLAW SAFETY] Layer not ready.")
        except Exception as e:
            print(f"[CLAW SAFETY ERROR] {e}")

        # === BLOCKREASONER SELF-EVOLUTION (this is the learning part) ===
        if hasattr(self.agent, 'block_reasoner'):
            try:
                self.agent.block_reasoner.self_evolve(num_steps=5)  # learns from this cycle
            except Exception as e:
                print(f"[BLOCK] Self-evolve skipped: {e}")

        self.agent.stats["improvement_cycles"] = self.agent.stats.get("improvement_cycles", 0) + 1
        self.agent.mark_dirty()
        self._last_cycle = time.time()
        return "✅ Self-improvement cycle completed with Claw safety review + BlockReasoner evolution."

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
        """Full AutoDream cycle — now rate-limited."""
        if time.time() - self._last_cycle < 180:   # 3 minutes minimum
            return

        print(f"[AUTODREAM] Starting full maintenance cycle @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        
        self._parse_traces_for_atomic_facts()
        self._decay_importance()
        self.run_self_improvement_cycle()
        
        # Light journal at end of dream
        if random.random() < 0.6:
            self._create_journal_entry(force=False)
        
        print(f"[AUTODREAM] Cycle completed @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.agent.mark_dirty()

        self.agent.state.stats["auto_dream_runs"] = self.agent.state.stats.get("auto_dream_runs", 0) + 1
        self.agent.state.mark_dirty()
        print(f"[AUTODREAM] Cycle completed — Total runs: {self.agent.state.stats['auto_dream_runs']}")

        # Run decay
        if hasattr(self.agent.memory, 'decay_manager'):
            decay_result = self.agent.memory.decay_manager.run_decay()
            print(decay_result)

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
                    time.sleep(180)
                    if random.random() < 0.7:
                        self.run_daemons()
                except Exception:
                    time.sleep(60)

        thread = threading.Thread(target=daemon_loop, daemon=True)
        thread.start()

        print("[AUTONOMOUS] Background daemons started (journaling, reflection, Hall of Records archiving active)")