"""
Genesis v5.6.9 Cerberus OmniPalace — Self Improvement
Clean version with journal-guided learning.
"""

from __future__ import annotations

import shutil
import re
from pathlib import Path
import sys
from datetime import datetime

from .config import TRACE_DIR, CONFIG
from .dependencies import HAS_DIFF
from .utils import dump_trace


def auto_improve_and_test(state: "AgentMemory", dry_run: bool = True):
    """Manual self-improvement cycle."""
    dump_trace("self_improvement", {"mode": "manual", "dry_run": dry_run})
    print("\n [IMPROVE-AUTO] Starting intelligent self-improvement cycle...\n")

    # Context
    wiki_count = len(list(state.memory.wiki_dir.rglob("*.md"))) if hasattr(state.memory, 'wiki_dir') else 0
    recent_journals = "No recent journals."
    try:
        journals = [line for line in state.index.index_lines if "topic=journal" in line][-5:]
        if journals:
            recent_journals = "\n".join(journals[-3:])
    except:
        pass

    context = f"Level: {state.level} | XP: {state.total_xp} | Wiki pages: {wiki_count} | Journals: {recent_journals[:200]}"

    system_prompt = "You are a careful, security-conscious code evolution agent."
    user_prompt = f"""Review your code and recent journals. Suggest exactly ONE safe improvement.

Context: {context}

Respond in this exact format:

### PROPOSAL
Title

### REASON
Why

### EXPECTED BENEFIT
Benefit

### DIFF
```diff
--- file.py
+++ file.py
@@ -1,3 +1,3 @@
-old
+new
```"""

    proposal = state.call_llm_safe(system_prompt, user_prompt)

    print("="*80)
    print("GENESIS SELF-IMPROVEMENT PROPOSAL")
    print("="*80)
    print(proposal)
    print("="*80)

    diff_match = re.search(r"```diff\n(.*?)\n```", proposal, re.DOTALL)
    if not diff_match:
        print(" [ERROR] No diff found.")
        return

    diff_block = diff_match.group(1).strip()

    if dry_run:
        print(" [DRY-RUN] Proposal shown. No changes applied.")
        return

    # Backup and apply
    script_path = Path(sys.argv[0]).resolve()
    backup_path = script_path.with_suffix(f".bak.v{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(script_path, backup_path)
    print(f"Backup created: {backup_path.name}")

    try:
        if HAS_DIFF:
            import diff_match_patch
            dmp = diff_match_patch.diff_match_patch()
            patches = dmp.patch_fromText(diff_block)
            with open(script_path, "r", encoding="utf-8") as f:
                original = f.read()
            patched, results = dmp.patch_apply(patches, original)
            if all(results):
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(patched)
                print("✅ Patch applied successfully!")
            else:
                print("Patch partially failed.")
        else:
            print("[WARNING] diff_match_patch not available.")
    except Exception as e:
        print(f"Error applying patch: {e}")
        shutil.copy2(backup_path, script_path)


if __name__ == "__main__":
    print("self_improvement.py loaded successfully.")