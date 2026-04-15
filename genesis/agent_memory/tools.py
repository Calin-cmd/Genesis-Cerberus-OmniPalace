"""
Genesis v5.6.9 Cerberus OmniPalace — ToolRegistry
Production version with robust path resolution and full news/web search.
"""

from __future__ import annotations

import subprocess
import shlex
from pathlib import Path
from datetime import datetime
from typing import Dict, Callable, List, Any

from ..config import CONFIG
from ..config import log_status, STORAGE_DIR
from ..notification import ProactiveTools, SecureNotificationLogger
from .core import AgentMemory


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self, agent: "AgentMemory"):
        self.tools: Dict[str, Dict] = {}
        self.functions: Dict[str, Callable] = {}
        self.agent = agent
        self.logger = SecureNotificationLogger()
        self._register_default_tools()

    def register(self, name: str, schema: Dict, func: Callable):
        self.tools[name] = schema
        self.functions[name] = func
        log_status(f"[TOOL] Registered: {name}")

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())

    def execute(self, name: str, args: Dict = None) -> str:
        if name not in self.functions:
            return f"Tool '{name}' not found"
        try:
            result = self.functions[name](**(args or {}))
            return str(result) if result is not None else "Tool executed successfully"
        except Exception as e:
            print(f"[TOOL ERROR] {name}: {e}")
            return f"Tool '{name}' error: {e}"

    def _register_default_tools(self):
        """Register all tools."""

        def _tool_notify(title: str = "Genesis", message: str = "", **kwargs):
            ProactiveTools.push_notification(title, message)
            return "Notification delivered"

        def _tool_schedule(minutes: int = 5, action: str = "notify", custom_prompt: str = None, **kwargs):
            try:
                minutes = int(minutes)
            except:
                minutes = 5
            return ProactiveTools.schedule_action(minutes, action, custom_prompt)

        def _tool_send_file(filename: str = "output.txt", content: str = "", **kwargs):
            return ProactiveTools.send_file(filename, content)

        def _tool_journal(**kwargs):
            return self.agent.autonomous._create_journal_entry(force=True) if hasattr(self.agent.autonomous, '_create_journal_entry') else "Journal created"

        def _tool_coherence(**kwargs):
            return self.agent.run_coherence_check() if hasattr(self.agent, 'run_coherence_check') else "Coherence check unavailable"

        def _tool_reflect(**kwargs):
            return self.agent.run_reflection(force=True) if hasattr(self.agent, 'run_reflection') else "Reflection unavailable"

        def _tool_predict(**kwargs):
            return self.agent.generate_forward_predictions(force=True) if hasattr(self.agent, 'generate_forward_predictions') else "Predictions unavailable"

        def _tool_music(style: str = "focus", **kwargs):
            return ProactiveTools.play_music(style) or f"Music mode: {style}"

        # Web search
        def _tool_web_search(query: str = "", max_results: int = 6, **kwargs):
            if not query or len(query.strip()) < 3:
                return "Please provide a search query."
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return f"No results found for: '{query}'"

                output = [f"🔍 Web Search: '{query}'"]
                for i, r in enumerate(results, 1):
                    output.append(f"{i}. {r.get('title', 'No title')}")
                    output.append(f"   {r.get('href', '')}")
                    output.append(f"   {r.get('body', r.get('snippet', ''))[:280]}...\n")
                
                result = "\n".join(output)

                # === RESTORED ORIGINAL VISION: Auto-ingest world knowledge to OmniPalace + Hall of Records ===
                if hasattr(self.agent, 'omnipalace'):
                    self.agent.omnipalace.add_atomic(result, tags=["world", "web_search", "tool"])
                if hasattr(self.agent, 'autonomous'):
                    try:
                        self.agent.autonomous._create_journal_entry(force=False)
                    except:
                        pass

                return result
            except Exception as e:
                return f"Web search failed: {str(e)[:150]}"

        # News search
        def _tool_news_search(query: str = "", max_results: int = 8, **kwargs):
            if not query:
                return "Please provide a news query."
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.news(query, max_results=max_results))
                if not results:
                    return f"No news found for: '{query}'"

                output = [f"📰 News for '{query}'"]
                for i, r in enumerate(results, 1):
                    output.append(f"{i}. {r.get('title', 'No title')}")
                    output.append(f"   {r.get('href', '')}")
                    output.append(f"   {r.get('body', r.get('snippet', ''))[:280]}...\n")
                
                result = "\n".join(output)

                # === RESTORED ORIGINAL VISION: Auto-ingest world knowledge to OmniPalace + Hall of Records ===
                if hasattr(self.agent, 'omnipalace'):
                    self.agent.omnipalace.add_atomic(result, tags=["world", "news_search", "tool"])
                if hasattr(self.agent, 'autonomous'):
                    try:
                        self.agent.autonomous._create_journal_entry(force=False)
                    except:
                        pass

                return result
            except Exception as e:
                return f"News search failed: {str(e)[:150]}"

        def _tool_wikipedia_search(query: str = "", sentences: int = 3, **kwargs):
            if not query:
                return "Please provide a query."
            try:
                import wikipedia
                wikipedia.set_lang("en")
                results = wikipedia.search(query, results=5)
                if not results:
                    return "No Wikipedia results."
                summary = wikipedia.summary(results[0], sentences=sentences)
                return f"📖 Wikipedia: {results[0]}\n\n{summary}"
            except Exception as e:
                return f"Wikipedia failed: {e}"

        # Read own code - robust path resolution
        def _tool_read_own_code(filename: str = None, **kwargs):
            possible_roots = [
                Path(__file__).parent.parent.parent.resolve(),
                Path.cwd().resolve(),
                Path("C:/Users/strat/genesis_modular").resolve(),
                Path.home() / "genesis_modular"
            ]

            if filename:
                for root in possible_roots:
                    path = root / filename
                    if path.exists():
                        content = path.read_text(encoding="utf-8")
                        return f"📄 Content of {filename} ({len(content)} chars):\n\n{content[:4000]}\n... (truncated)"
                return f"File not found: {filename} (tried multiple roots)"

            # List key files
            key_files = [
                "run.py",
                "genesis/agent_memory/core.py",
                "genesis/agent_memory/tools.py",
                "genesis/agent_memory/conversation.py",
                "genesis/agent_memory/memory.py",
                "genesis/agent_memory/commands.py",
                "genesis/self_improvement_daemon.py"
            ]
            result = "Available source files for self-improvement:\n"
            for f in key_files:
                found = False
                for root in possible_roots:
                    p = root / f
                    if p.exists():
                        size = p.stat().st_size
                        result += f"• {f} ({size} bytes) [FOUND]\n"
                        found = True
                        break
                if not found:
                    result += f"• {f} (not found)\n"
            result += "\nExample: read_own_code(filename='genesis/agent_memory/tools.py')"
            return result

        # Wiki tools
        def _tool_wiki_compile(path: str = None, **kwargs):
            return self.agent.compile_obsidian_vault(path) if hasattr(self.agent, 'compile_obsidian_vault') else "Wiki unavailable"

        def _tool_wiki_heal(depth: str = "light", **kwargs):
            return self.agent.heal_wiki(depth) if hasattr(self.agent, 'heal_wiki') else "Wiki healing unavailable"

        def _tool_wiki_status(**kwargs):
            return self.agent.get_wiki_status() if hasattr(self.agent, 'get_wiki_status') else {"wiki_pages": 0}

        # Safe file tools
        def _tool_read_file(filepath: str, **kwargs):
            return _safe_read_file(filepath)

        def _tool_write_file(filepath: str, content: str, **kwargs):
            return _safe_write_file(filepath, content)

        def _tool_edit_file(filepath: str, diff: str, **kwargs):
            return _safe_edit_file_with_confirmation(filepath, diff)

        def _tool_run_bash(command: str, **kwargs):
            return _safe_run_bash(command)

        # Register all tools
        registrations = [
            ("notify", {}, _tool_notify),
            ("schedule", {}, _tool_schedule),
            ("send_file", {}, _tool_send_file),
            ("journal", {}, _tool_journal),
            ("coherence", {}, _tool_coherence),
            ("reflect", {}, _tool_reflect),
            ("predict", {}, _tool_predict),
            ("music", {}, _tool_music),
            ("web_search", {}, _tool_web_search),
            ("news_search", {}, _tool_news_search),
            ("wikipedia_search", {}, _tool_wikipedia_search),
            ("read_own_code", {}, _tool_read_own_code),
            ("wiki_compile", {}, _tool_wiki_compile),
            ("wiki_heal", {}, _tool_wiki_heal),
            ("wiki_status", {}, _tool_wiki_status),
            ("read_file", {}, _tool_read_file),
            ("write_file", {}, _tool_write_file),
            ("edit_file", {}, _tool_edit_file),
            ("run_bash", {}, _tool_run_bash),
        ]

        for name, schema, func in registrations:
            self.register(name, schema, func)

        log_status(f"[TOOL REGISTRY] {len(self.tools)} tools registered successfully")

# ====================== SAFE HELPERS ======================
def _resolve_safe_path(filepath: str) -> Path:
    bases = [
        Path.cwd().resolve(),
        Path(__file__).parent.parent.parent.resolve(),
        Path("C:/Users/strat/genesis_modular").resolve(),
        Path.home() / "genesis_modular"
    ]
    for base in bases:
        p = (base / filepath).resolve()
        if p.exists() and str(base) in str(p):
            return p
    return Path(filepath).resolve()

def _safe_read_file(filepath: str) -> str:
    try:
        safe_path = _resolve_safe_path(filepath)
        if not safe_path.exists():
            return f"File not found: {filepath}"
        content = safe_path.read_text(encoding="utf-8")
        return f"📄 {filepath}:\n\n{content[:8000]}"
    except Exception as e:
        return f"Read failed: {e}"

def _safe_write_file(filepath: str, content: str) -> str:
    try:
        safe_path = _resolve_safe_path(filepath)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")
        ProactiveTools.push_notification("File Written", f"Saved {filepath}")
        return f"✅ Wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Write failed: {e}"

def _safe_edit_file_with_confirmation(filepath: str, diff: str) -> str:
    try:
        safe_path = _resolve_safe_path(filepath)
        if not safe_path.exists():
            return f"File does not exist: {filepath}"

        dangerous = ["rm -rf", "shutil.rmtree", "os.system", "subprocess", "exec(", "eval("]
        if any(d in diff.lower() for d in dangerous):
            return "❌ Dangerous patch blocked."

        print(f"\n⚠️ Proposed edit to: {filepath}")
        print(diff[:800] + ("..." if len(diff) > 800 else ""))
        confirm = input("Apply this edit? [y/N]: ").strip().lower()
        if confirm not in ('y', 'yes'):
            return "❌ Edit cancelled."

        backup = safe_path.with_suffix(safe_path.suffix + f".bak.{datetime.now():%H%M%S}")
        safe_path.rename(backup)

        try:
            import diff_match_patch
            dmp = diff_match_patch.diff_match_patch()
            patches = dmp.patch_fromText(diff)
            with open(safe_path, "r", encoding="utf-8") as f:
                original = f.read()
            patched, results = dmp.patch_apply(patches, original)
            if all(results):
                safe_path.write_text(patched, encoding="utf-8")
                ProactiveTools.push_notification("File Edited", f"Patched {filepath}")
                return f"✅ Edit applied. Backup: {backup.name}"
            else:
                safe_path.write_text(original, encoding="utf-8")
                return "❌ Patch failed. Reverted."
        except ImportError:
            safe_path.write_text(diff, encoding="utf-8")
            return f"✅ File overwritten (diff library not available). Backup: {backup.name}"

    except Exception as e:
        return f"Edit failed: {e}"

def _safe_run_bash(command: str, **kwargs) -> str:
    whitelist = {"ls", "pwd", "cat", "echo", "head", "tail", "grep", "find", "wc", "date", "whoami"}
    cmd_lower = command.strip().lower().split()[0] if command.strip() else ""
    if cmd_lower not in whitelist:
        return f"❌ Command '{cmd_lower}' not allowed."
    try:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True, timeout=10, cwd=STORAGE_DIR / "sandbox")
        output = result.stdout or result.stderr
        return f"🖥️ {command}\n{output.strip()[:1500]}"
    except Exception as e:
        return f"Bash error: {e}"


if __name__ == "__main__":
    print("ToolRegistry loaded successfully.")