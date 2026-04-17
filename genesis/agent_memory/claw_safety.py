"""
Claw Self-Improvement Safety Layer - Simplified & Robust
"""

from pathlib import Path
from datetime import datetime
from ..config import log_status

class ClawSafety:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        print("[CLAW SAFETY] Initialized in safe mode (review-only)")

    def review_and_apply_patch(self, patch_content: str, description: str) -> str:
        """Safe review-only mode. No automatic git changes."""
        try:
            safe_preview = patch_content[:800] + "..." if len(patch_content) > 800 else patch_content
            
            return f"""🛡️ CLAW SAFETY REVIEW REQUIRED

Description: {description}

Proposed Change Preview:
{safe_preview}

✅ This change is in REVIEW MODE only.
Reply with:
/approve - to apply this improvement
/reject  - to discard it
"""
        except Exception as e:
            return f"[CLAW SAFETY] Review failed: {e}"

    def approve_patch(self):
        """Apply the approved patch safely."""
        try:
            # For now: Log the approved change and simulate application
            # In the next phase we can make it write to files + git commit
            log_status(f"[CLAW] Patch approved at {datetime.now()}")
            
            # Future: Write patch to proposed_patches/ folder and auto-apply
            patch_dir = self.repo_root / "proposed_patches"
            patch_dir.mkdir(exist_ok=True)
            patch_file = patch_dir / f"approved_patch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            patch_file.write_text("Patch approved by user.\n\nThis will be auto-applied in the next version of Claw.")
            
            return "✅ Patch approved and logged for application. (Safe mode - no files changed yet)"
        except Exception as e:
            return f"❌ Failed to process approval: {e}"

    def reject_patch(self):
        return "🛡️ Patch rejected."