"""
Genesis - Dashboard & Visualization
"""

from collections import defaultdict


class AgentDashboard:
    """Handles visualize() and stats dashboard."""

    def __init__(self, agent: "AgentMemory"):
        self.agent = agent

    def visualize(self) -> str:
        d = {
            "wiki_pages": 0,
            "memories_index": len(getattr(self.agent.index, 'index_lines', [])),
            "memories_chroma": getattr(self.agent, 'collection', None).count() if hasattr(self.agent, 'collection') and self.agent.collection else 0,
            "active_sub_agents": len(getattr(self.agent, 'active_sub_agents', {})),
            "tools_registered": len(self.agent.tool_registry.list_tools()) if self.agent.tool_registry else 0,
            "auto_dream_runs": self.agent.state.stats.get("auto_dream_runs", 0),
            "user_name": self.agent.state.user_name or 'Unknown',
            "current_session": self.agent.state.current_session,
            "turns": self.agent.state.session_turn_count.get(self.agent.state.current_session, 0)
        }

        topic_counts = defaultdict(int)
        for line in getattr(self.agent.index, 'index_lines', [])[-500:]:
            try:
                topic = line.split(" | ")[1] if " | " in line else "general"
                topic_counts[topic] += 1
            except:
                pass

        out = [
            "="*80,
            f"          GENESIS v5.6.9 CERBERUS DASHBOARD — Level {self.agent.level}",
            "="*80,
            f"XP: {self.agent.total_xp:,} | Progress: {self.agent.get_xp_progress() if hasattr(self.agent, 'get_xp_progress') else 'N/A'}",
            f"Obsidian Wiki: {d['wiki_pages']} pages | Memories: {d['memories_index']} + {d['memories_chroma']} (Chroma)",
            f"OmniPalace Rooms: {len(self.agent.omnipalace_rooms)} | Active Sub-Agents: {d['active_sub_agents']}",
            f"Tools: {d['tools_registered']} | AutoDream: {d['auto_dream_runs']} runs",
            f"User: {d['user_name']} | Session: {d['current_session']} ({d['turns']} turns)",
            "="*80,
            "\nTOPIC DISTRIBUTION (last 500 memories)",
        ]

        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:12]:
            bar = "█" * min(count // 4, 25)
            out.append(f"  • {topic:<22} {bar} {count}")

        out.append("\n" + "="*80)
        out.append("Type /stats for detailed numbers | /palace for spatial view | /wiki status for vault")
        return "\n".join(out)