"""
Genesis v5.6.9 Cerberus OmniPalace — Utils
Utility functions including rich trace system for hallucination detection,
atomic fact extraction, and Obsidian Wiki support.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .config import TRACE_DIR, CONFIG


# ====================== RICH TRACE SYSTEM ======================
def dump_trace(event_type: str, data: dict):
    """
    Rich structured tracing for internal LLM thoughts, decisions, and actions.
    Designed specifically for hallucination detection and atomic fact extraction by AutoDream.
    """
    if not CONFIG.get("trace_enabled", True):
        return

    trace = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "thought_id": f"thought_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}",
        "session": "global",
        **data
    }

    # Rich metadata for atomic fact extraction
    if "stage" in data:
        trace["stage"] = data["stage"]
    if "reason" in data or "reasoning" in data:
        trace["reasoning"] = data.get("reason") or data.get("reasoning")
    if "response_length" in data:
        trace["output_tokens"] = data.get("response_length", 0)
    if "preheat_length" in data:
        trace["preheat_tokens"] = data.get("preheat_length", 0)
    if "retrieved_count" in data:
        trace["retrieved_items"] = data.get("retrieved_count", 0)
    if "cerberus_decision" in data:
        trace["used_cerberus"] = data.get("cerberus_decision", False)
    if "tools_detected" in data or "tools_used" in data:
        trace["tools_used"] = True
    if "final_response_preview" in data:
        trace["response_preview"] = data.get("final_response_preview", "")[:200]

    # Add context for atomic fact parsing
    trace["extractable_for_facts"] = True

    trace_file = TRACE_DIR / f"{datetime.now().strftime('%Y%m%d')}.jsonl"

    try:
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Silent fail — tracing must never break core functionality


def get_trace_summary(days: int = 1) -> str:
    """Utility to summarize recent traces (useful for /stats or debugging)."""
    try:
        today = datetime.now().strftime('%Y%m%d')
        trace_file = TRACE_DIR / f"{today}.jsonl"
        
        if not trace_file.exists():
            return "No traces recorded today."

        lines = trace_file.read_text(encoding="utf-8").splitlines()[-100:]  # Last 100 events
        events = [json.loads(line) for line in lines if line.strip()]

        summary = f"Recent traces ({len(events)} events):\n"
        event_counts = {}
        for e in events:
            et = e.get("event_type", "unknown")
            event_counts[et] = event_counts.get(et, 0) + 1

        for event, count in sorted(event_counts.items(), key=lambda x: -x[1]):
            summary += f"  • {event:<25} : {count}\n"

        return summary.strip()
    except Exception as e:
        return f"Could not read traces: {e}"


# ====================== ADDITIONAL UTILITIES ======================
def safe_filename(name: str, extension: str = ".txt") -> str:
    """Sanitize filename for safe file operations."""
    import re
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', name.strip())
    if not safe.lower().endswith(extension.lower()):
        safe += extension
    return safe


def truncate_text(text: str, max_length: int = 300, suffix: str = "...") -> str:
    """Safely truncate text with word boundary awareness."""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.7:
        truncated = truncated[:last_space]
    return truncated + suffix


# ====================== WIKI SPECIFIC UTILITIES ======================
def get_wiki_path() -> Path:
    """Return the Obsidian vault wiki directory path."""
    from .config import STORAGE_DIR
    return STORAGE_DIR / "obsidian_vault" / "wiki"


def count_wiki_pages() -> int:
    """Count current Obsidian wiki pages."""
    try:
        wiki_dir = get_wiki_path()
        return len(list(wiki_dir.rglob("*.md")))
    except:
        return 0


# For debugging
if __name__ == "__main__":
    print("Utils loaded successfully with rich tracing support for atomic fact extraction.")
    print(f"Current wiki pages: {count_wiki_pages()}")
    print("Safe filename test:", safe_filename("My Test File!.txt"))