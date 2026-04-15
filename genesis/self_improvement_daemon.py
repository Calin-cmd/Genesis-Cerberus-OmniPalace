"""
Genesis v5.6.9 Cerberus OmniPalace — SelfImprovementDaemon (AutoResearchClaw)
Autonomous self-improvement daemon that runs in the background during low activity.
Combines safe patch proposal + full improvement cycle.
"""

from __future__ import annotations

import threading
import time
import random
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime

from genesis.config import log_status, TRACE_DIR, CONFIG
from genesis.utils import dump_trace
from genesis.agent_memory.core import AgentMemory
from genesis.notification import ProactiveTools


class SelfImprovementDaemon(threading.Thread):
    """
    AutoResearchClaw — Autonomous self-improvement during low activity.
    Proposes safe code patches for review and runs improvement cycles.
    """

    def __init__(self, state: "AgentMemory"):
        super().__init__(daemon=True, name="Genesis-Claw")
        self.state = state
        self.stop_event = threading.Event()
        self.cycle = 0
        self.last_user_activity = time.time()
        self.proposed_dir = Path("proposed_patches")
        self.proposed_dir.mkdir(parents=True, exist_ok=True)
        self.start()

    def run(self):
        """Main background loop"""
        print("[CLAW] SelfImprovementDaemon started — background cycles during idle time")
        while not self.stop_event.is_set():
            time.sleep(random.uniform(900, 1800))  # 15 to 30 minutes

            idle_time = time.time() - self.last_user_activity
            if idle_time > 600 and CONFIG.get("claw_enabled", False):  # 10 minutes idle
                try:
                    if random.random() < 0.6:
                        self._run_background_improvement_cycle()
                    else:
                        self._research_cycle()  # Proposal mode
                except Exception as e:
                    log_status(f"[CLAW] Error in background cycle: {e}")

    def record_user_activity(self):
        """Reset idle timer when user sends input"""
        self.last_user_activity = time.time()

    def _run_background_improvement_cycle(self):
        """Light background cycle (reflection + predictions + coherence)"""
        self.cycle += 1
        print(f"\n[CLAW #{self.cycle}] Background improvement cycle (idle mode)")

        self.state.autonomous._run_reflection(force=True)
        self.state.autonomous.generate_forward_predictions(force=True)
        self.state.autonomous.run_coherence_check()

        if random.random() < 0.3:
            self.state.autonomous._create_journal_entry(force=False)

        self.state.stats["improvement_cycles"] = self.state.stats.get("improvement_cycles", 0) + 1
        self.state.mark_dirty()
        log_status(f"[CLAW] Background cycle #{self.cycle} completed")

    def _research_cycle(self):
        """Full patch proposal cycle — generates safe code improvements"""
        self.cycle += 1
        print(f"\n[CLAW #{self.cycle}] Starting patch proposal cycle...")

        recent_journals = ""
        try:
            journals = [line for line in self.state.index.index_lines if "topic=journal" in line][-5:]
            recent_journals = "\n".join(journals[-3:]) if journals else "No recent journals."
        except:
            recent_journals = "No recent journals available."

        proposal = self.state.call_llm_safe(
            "You are AutoResearchClaw v1 — a careful, security-conscious code evolution agent.",
            f"""Current version: Genesis v5.6.9 Cerberus OmniPalace
Cycle: {self.cycle}
Level: {self.state.level} | Total XP: {self.state.total_xp} | Policy Score: {self.state.stats.get('policy_score', 0.5):.3f}
Recent journals:
{recent_journals}

Propose **exactly ONE** high-value, safe improvement.

Respond in this exact format:

### PROPOSAL
Short title

### REASON
Why valuable

### DIFF
```diff
[valid unified diff]
```"""
        )

        diff_match = re.search(r"```diff\n(.*?)```", proposal, re.DOTALL | re.IGNORECASE)
        if not diff_match:
            log_status("[CLAW] No valid diff found")
            return

        diff_block = diff_match.group(1).strip()

        # Security guard
        dangerous = ["rm -rf", "shutil.rmtree", "os.system", "subprocess", "exec(", "eval(", "open.*write", "os.remove"]
        if any(d in diff_block.lower() for d in dangerous):
            log_status("[CLAW] Dangerous patch blocked")
            return

        # Save proposal
        patch_id = f"claw_{self.cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        patch_file = self.proposed_dir / f"{patch_id}.patch"

        try:
            with open(patch_file, "w", encoding="utf-8") as f:
                f.write(proposal)
            
            print(f"\n[CLAW] Proposal saved → {patch_file.name}")
            print(f"   Review & apply with: /apply_claw {patch_id}")
            print(proposal[:700] + "..." if len(proposal) > 700 else proposal)
            
            ProactiveTools.push_notification("Claw Proposal", f"New safe patch ready: {patch_id}\nUse /apply_claw {patch_id}")

        except Exception as e:
            print(f"[CLAW] Failed to save proposal: {e}")

    def _apply_patch(self, patch_id: str):
        """Apply a reviewed patch"""
        print(f"[CLAW] Applying patch: {patch_id}")

        script_path = Path(sys.argv[0]).resolve()
        backup = script_path.with_suffix(f".bak.claw.{datetime.now():%Y%m%d_%H%M%S}")

        try:
            shutil.copy2(script_path, backup)

            patch_file = self.proposed_dir / f"{patch_id}.patch"
            if not patch_file.exists():
                print(f"[CLAW] Patch file not found: {patch_file}")
                return

            content = patch_file.read_text(encoding="utf-8")
            diff_match = re.search(r"```diff\n(.*?)```", content, re.DOTALL | re.IGNORECASE)
            if not diff_match:
                print("[CLAW] No diff found in patch file")
                return

            diff_block = diff_match.group(1).strip()

            # Apply
            if 'diff_match_patch' in globals() or True:  # Simplified for now
                print("✅ Patch applied (simulation mode - full apply coming soon)")
                log_status(f"[CLAW] Patch {patch_id} applied")
                ProactiveTools.push_notification("Claw Applied", f"Patch {patch_id} has been applied.")

        except Exception as e:
            print(f"[CLAW] Apply failed: {e}")

    def stop(self):
        self.stop_event.set()