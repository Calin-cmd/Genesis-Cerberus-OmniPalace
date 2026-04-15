"""
Genesis v5.6.9 Cerberus OmniPalace — CommandRouter
"""

from __future__ import annotations
import re
from typing import Optional

from ..config import HELP_TEXT, FULL_HELP_TEXT, CONFIG, RAG_MODEL
from ..notification import ProactiveTools
from .core import AgentMemory


class CommandRouter:
    """Full command router for Genesis with all features."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent

    def handle(self, user_input: str) -> Optional[str]:
        """Main command router."""
        if not user_input.strip().startswith('/'):
            return None

        cmd = user_input.strip().lower()
        response = None

        # ====================== CORE & SESSION ======================
        if cmd in ("/help", "/h"):
            response = HELP_TEXT

        elif cmd in ("/fullhelp", "/full", "/full help", "/help full"):
            response = FULL_HELP_TEXT

        elif cmd in ("/stats", "/status"):
            response = self.agent.get_stats() if hasattr(self.agent, 'get_stats') else "Stats unavailable."

        elif cmd in ("/visualize", "/viz"):
            response = self.agent.visualize() if hasattr(self.agent, 'visualize') else "Visualization unavailable."

        elif cmd in ("/xp", "/level", "/progress"):
            response = self.agent.xp.show_xp_breakdown() if hasattr(self.agent, 'xp') and hasattr(self.agent.xp, 'show_xp_breakdown') else "XP system initializing..."

        elif cmd in ("/personality", "/traits", "/whoareyou"):
            response = self.agent.xp.show_personality() if hasattr(self.agent, 'xp') and hasattr(self.agent.xp, 'show_personality') else "Personality profile building..."

        elif cmd in ("/new", "/reset"):
            self.agent.reset_session(hard_reset=False)
            response = f"✅ New session started: {self.agent.current_session} (token budget reset)"

        # ====================== MEMORY & SEARCH ======================
        elif cmd.startswith("/search"):
            query = user_input[7:].strip()
            if query and hasattr(self.agent.memory, 'search'):
                results = self.agent.memory.search(query)
                response = f"🔍 Search results for '{query}':\n{results}"
            else:
                response = "Usage: /search <query>"

        # ====================== CERBERUS ======================
        elif cmd.startswith("/debate"):
            topic = user_input[7:].strip() or "general discussion"
            response = self.agent.cerberus.run_with_context(topic) if hasattr(self.agent, 'cerberus') else "Cerberus unavailable."

        # ====================== AUTONOMOUS ======================
        elif cmd == "/journal":
            response = self.agent.autonomous._create_journal_entry(force=True) if hasattr(self.agent.autonomous, '_create_journal_entry') else "Journal unavailable."

        elif cmd == "/reflect":
            response = self.agent.run_reflection(force=True) if hasattr(self.agent, 'run_reflection') else "Reflection unavailable."

        elif cmd == "/coherence":
            response = self.agent.run_coherence_check() if hasattr(self.agent, 'run_coherence_check') else "Coherence check unavailable."

        elif cmd == "/auto-dream":
            if hasattr(self.agent.autonomous, '_run_full_auto_dream'):
                self.agent.autonomous._run_full_auto_dream()
                response = "✅ AutoDream cycle completed."
            else:
                response = "AutoDream unavailable."

        elif cmd == "/audit":
            response = self.agent.autonomous._run_full_audit() if hasattr(self.agent.autonomous, '_run_full_audit') else "Audit unavailable."

        elif cmd == "/nudge":
            response = self.agent.run_autonomous_nudge() if hasattr(self.agent, 'run_autonomous_nudge') else "Nudge unavailable."

        elif cmd == "/improve-auto":
            response = self.agent.autonomous.run_self_improvement_cycle() if hasattr(self.agent.autonomous, 'run_self_improvement_cycle') else "Self-improvement unavailable."

        # ====================== FEEDBACK ======================
        elif cmd.startswith(("/good", "/wrong", "/important")):
            action = cmd.split()[0][1:]
            entry_id = cmd.split()[1] if len(cmd.split()) > 1 else None
            response = self.agent.apply_feedback(action, entry_id) if hasattr(self.agent, 'apply_feedback') else "Feedback system initializing..."

        # ====================== SCHEDULING ======================
        elif cmd.startswith("/schedule"):
            response = self._handle_schedule(user_input)

        # ====================== PALACE ======================
        elif cmd.startswith("/palace"):
            response = self._handle_palace(user_input)

        elif cmd == "/visualize_3d" or cmd == "/3d":
            if hasattr(self.agent, 'omnipalace'):
                return self.agent.omnipalace.export_3d_palace()
            return "OmniPalace not initialized."

        # ====================== GRAPH ======================
        elif cmd.startswith("/graph"):
            response = self._handle_graph(user_input)

        # ====================== WIKI ======================
        elif cmd.startswith("/wiki"):
            response = self._handle_wiki(user_input)

        elif cmd.startswith("/obsidian"):
            response = self._handle_obsidian()

        # ====================== CLAW PATCH APPLICATION ======================
        elif cmd.startswith("/apply_claw"):
            patch_id = user_input[11:].strip()
            if not patch_id:
                response = "Usage: /apply_claw <patch_id>\nExample: /apply_claw claw_5_20260412_143022"
            else:
                # Delegate to Claw daemon if available
                if hasattr(self.agent, 'claw') and hasattr(self.agent.claw, '_apply_patch'):
                    try:
                        self.agent.claw._apply_patch(patch_id)
                        response = f"✅ Applied Claw patch: {patch_id}"
                    except Exception as e:
                        response = f"❌ Failed to apply patch {patch_id}: {e}"
                elif hasattr(self.agent.autonomous, 'claw') and hasattr(self.agent.autonomous.claw, '_apply_patch'):
                    try:
                        self.agent.autonomous.claw._apply_patch(patch_id)
                        response = f"✅ Applied Claw patch: {patch_id}"
                    except Exception as e:
                        response = f"❌ Failed to apply patch {patch_id}: {e}"
                else:
                    response = f"Claw daemon not available or patch {patch_id} not found.\nCheck the proposed_patches/ folder."

        # ====================== CREATE / CLEANUP / PLAN ======================
        elif cmd.startswith("/create"):
            response = self._handle_create(user_input)

        elif cmd == "/cleanup":
            archived = self.agent.memory.cleanup_old_memories() if hasattr(self.agent.memory, 'cleanup_old_memories') else 0
            response = f"🧹 Cleanup completed. {archived} low-importance items archived."

        elif cmd.startswith("/plan"):
            task = user_input[6:].strip() or "general task"
            response = self.agent.cerberus.run_with_context(f"Create a detailed step-by-step plan for: {task}") if hasattr(self.agent, 'cerberus') else "Planning unavailable."

        elif cmd.startswith("/corefacts"):
            from ..config import CORE_FACTS
            response = f"Current core facts:\n\n{CORE_FACTS}"

        # ====================== TASKS & SKILLS ======================
        elif cmd in ("/tasks", "/tasklist"):
            response = self._list_tasks()

        elif cmd in ("/skills", "/skill", "/skilllist", "/listskills"):
            response = self._list_skills()

        elif cmd.startswith("/cancel"):
            task_id = user_input[7:].strip()
            response = self._cancel_task(task_id)

        # ====================== TOOLS & AGENTS ======================
        elif cmd in ("/tools", "/toollist"):
            tools = self.agent.tool_registry.list_tools() if hasattr(self.agent, 'tool_registry') else []
            response = f"Available tools ({len(tools)}): {', '.join(tools) if tools else 'None loaded'}"

        elif cmd in ("/agents", "/subagents", "/listagents"):
            response = self.agent.omnipalace.list_sub_agents() if hasattr(self.agent, 'omnipalace') else "Sub-agents unavailable."

        elif cmd.startswith("/agent "):
            agent_id = user_input[7:].strip()
            response = self.agent.omnipalace.agent_details(agent_id) if hasattr(self.agent, 'omnipalace') else "Agent details unavailable."

        # ====================== SAFE FILE & SHELL ======================
        elif cmd.startswith("/read"):
            path = user_input[5:].strip()
            response = self.agent.tool_registry.execute("read_file", {"filepath": path}) if hasattr(self.agent.tool_registry, 'execute') else "Tool unavailable."

        elif cmd.startswith("/write"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 3:
                path, content = parts[1], parts[2]
                response = self.agent.tool_registry.execute("write_file", {"filepath": path, "content": content}) if hasattr(self.agent.tool_registry, 'execute') else "Tool unavailable."
            else:
                response = "Usage: /write <filepath> <content>"

        elif cmd.startswith("/edit"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 3:
                path, diff = parts[1], parts[2]
                response = self.agent.tool_registry.execute("edit_file", {"filepath": path, "diff": diff}) if hasattr(self.agent.tool_registry, 'execute') else "Tool unavailable."
            else:
                response = "Usage: /edit <filepath> <unified diff>"

        elif cmd.startswith("/bash"):
            cmd_str = user_input[5:].strip()
            response = self.agent.tool_registry.execute("run_bash", {"command": cmd_str}) if hasattr(self.agent.tool_registry, 'execute') else "Tool unavailable."

        else:
            response = f"Unknown command: {user_input}\nType /help for the full list."

        # Log command usage
        if response and hasattr(self.agent, 'add'):
            self.agent.add(f"User used command: {user_input}", topic="command_usage", importance=0.76, tags=["meta"])

        return response

    # ====================== PRIVATE HANDLERS ======================
    def _handle_schedule(self, user_input: str) -> str:
        try:
            parts = user_input.split(maxsplit=3)
            minutes = int(parts[1])
            action = parts[2] if len(parts) > 2 else "notify"
            prompt = parts[3] if len(parts) > 3 else None
            return ProactiveTools.schedule_action(minutes, action, prompt)
        except:
            return "Usage: /schedule <minutes> <action> [prompt]"

    def _handle_wiki(self, user_input: str) -> str:
        parts = user_input.split(maxsplit=2)
        subcmd = parts[1].lower() if len(parts) > 1 else "status"
        arg = parts[2] if len(parts) > 2 else None

        if subcmd == "compile":
            return self.agent.compile_obsidian_vault(arg) if hasattr(self.agent, 'compile_obsidian_vault') else "Wiki unavailable."
        elif subcmd == "heal":
            depth = arg or "light"
            return self.agent.heal_wiki(depth) if hasattr(self.agent, 'heal_wiki') else "Wiki healing unavailable."
        else:
            status = self.agent.get_wiki_status() if hasattr(self.agent, 'get_wiki_status') else {"wiki_pages": 0}
            return f"📖 Obsidian Vault Status\nWiki pages: {status.get('wiki_pages', 0)}\nUse /wiki compile or drop files in raw/"

    def _handle_obsidian(self) -> str:
        status = self.agent.get_wiki_status() if hasattr(self.agent, 'get_wiki_status') else {"wiki_pages": 0}
        return f"🌟 Obsidian Vault Ready!\nWiki pages: {status.get('wiki_pages', 0)}\nLocation: {STORAGE_DIR / 'obsidian_vault'}"

    def _handle_palace(self, user_input: str) -> str:
        if not hasattr(self.agent, 'omnipalace'):
            return "OmniPalace not initialized."
        return self.agent.omnipalace.visualize_palace_map() if len(user_input.split()) < 2 else self.agent.omnipalace.enter_palace_room(" ".join(user_input.split()[2:])) if user_input.split()[1] in ("enter", "go") else self.agent.omnipalace.visualize_palace_map()

    def _handle_graph(self, user_input: str) -> str:
        return "Graph commands not fully implemented yet. Use /stats for overview."

    def _handle_create(self, user_input: str) -> str:
        parts = user_input.split(maxsplit=2)
        if len(parts) < 2:
            return "Usage: /create <skill|tool> <name>"
        item_type = parts[1].lower()
        name = parts[2] if len(parts) > 2 else "unnamed"
        self.agent.add(f"New {item_type}: {name}", topic=item_type, importance=0.85)
        return f"✅ Created {item_type}: {name}"

    def _list_tasks(self) -> str:
        return "Task scheduler overview: Use /schedule to create tasks."

    def _list_skills(self) -> str:
        return "Skills: Use /create skill <name> to build your skill library."

    def _cancel_task(self, task_id: str) -> str:
        return "Task cancellation not yet implemented."

    def _default_visualize(self) -> str:
        return f"Genesis v5.6.9\nLevel: {getattr(self.agent, 'level', 1)} | XP: {getattr(self.agent, 'total_xp', 0)}"