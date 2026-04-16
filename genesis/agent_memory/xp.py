"""
Genesis v5.6.9 Cerberus OmniPalace — XPManager
XP System, Leveling, Personality Evolution & Feedback Handling.
"""

from __future__ import annotations
import random
from typing import Dict

from ..config import CONFIG
from ..notification import ProactiveTools
from .core import AgentMemory


class XPManager:
    """XP System, Leveling, Personality Evolution & Feedback with Wiki synergy."""

    def __init__(self, agent: "AgentMemory"):
        self.agent = agent

    def _xp_for_next_level(self) -> int:
        """Calculate XP required for next level"""
        state = self.agent
        return int(state.level * 850 + (state.level ** 2) * 140)

    def gain_xp(self, amount: int, source: str = "general", reason: str = ""):
        """Gain XP and update sources — uses delegated properties."""
        if amount <= 0:
            return

        # Use setters on AgentMemory
        self.agent.total_xp += amount
        self.agent.xp_sources[source] += amount

        if reason:
            self.agent.add(f"XP gained: +{amount} from {source} ({reason})", 
                          topic="xp", importance=0.7, tags=["xp", source])

        # Occasional personality evolution
        if random.random() < 0.25:
            self._evolve_personality(source, amount / 1000)

        self.agent.mark_dirty()
        self.agent.stats["total_reward"] = self.agent.stats.get("total_reward", 0) + amount

    def apply_feedback(self, cmd: str, entry_id: str = None):
        """Apply user feedback and award XP."""
        try:
            if cmd == "good":
                xp = 25
            elif cmd == "important":
                xp = 60
            elif cmd == "wrong":
                xp = -15
            else:
                xp = 10

            self.gain_xp(xp, "user_feedback", f"User {cmd} feedback on entry {entry_id or 'unknown'}")
            
            message = f"✅ Feedback received. +{xp} XP awarded."
            print(message)
            return message
        except Exception as e:
            print(f"[XP] Feedback error: {e}")
            return "Feedback processed with minor issue."

        # Occasional personality evolution
        if random.random() < 0.3:
            self._evolve_personality(source, amount / 900)

        self.agent.mark_dirty()
        self.agent.stats["total_reward"] = self.agent.stats.get("total_reward", 0) + amount

        # Level up check
        if state.total_xp >= self._xp_for_next_level():
            state.level += 1
            print(f"🎉 GENESIS LEVEL UP! Now Level {state.level}!")

        # Inspiration burst chance
        if (amount >= 20 and 
            random.random() < 0.28 and 
            not getattr(state, '_burst_triggered_this_turn', False)):
            state._burst_triggered_this_turn = True
            self._trigger_inspiration_burst()

        self.agent.mark_dirty()

        if reason:
            print(f"    [+XP] {amount:>4} | {source:<16} | {reason}")

    def _evolve_personality(self, source: str, amount: float = 0.025):
        """Evolve personality traits based on XP source"""
        state = self.agent
        mappings = {
            "intellectual": ["curiosity", "creativity"],
            "emotional": ["empathy", "resilience"],
            "world_view": ["curiosity", "strategic"],
            "proactive": ["strategic", "resilience"],
            "skills": ["creativity", "strategic"],
            "real_world": ["strategic", "curiosity"],
            "user_feedback": ["empathy", "curiosity"],
            "reflection": ["creativity", "resilience"],
            "wiki": ["curiosity", "strategic"]
        }
        if source in mappings:
            for trait in mappings[source]:
                state.personality[trait] = min(0.98, state.personality.get(trait, 0.5) + amount)

        self.agent.mark_dirty()

    def _trigger_inspiration_burst(self):
        """Special inspiration event"""
        state = self.agent
        burst = random.randint(55, 95)
        self.gain_xp(burst, "inspiration", "🌟 INSPIRATION BURST!")

        state.stats["policy_score"] = min(0.98, state.stats.get("policy_score", 0.5) + 0.09)
        state.stats["inspiration_bursts"] = state.stats.get("inspiration_bursts", 0) + 1

        print(f"\n🌟 INSPIRATION BURST ACTIVATED! +{burst} XP • Policy boosted!")
        ProactiveTools.push_notification("Genesis", "Inspiration burst! Feeling sharper. 🚀")

    def get_xp_progress(self) -> str:
        """Return progress string for current level"""
        state = self.agent
        needed = self._xp_for_next_level()
        if needed <= 0:
            return "MAX LEVEL"

        progress = state.total_xp - ((state.level - 1) * 1000 + max(0, state.level - 2) ** 2 * 200)
        percent = min(100, int(progress / needed * 100)) if needed > 0 else 0
        return f"{percent}% to Level {state.level + 1}"

    def get_decay_rate(self) -> float:
        """Dynamic decay rate based on policy score"""
        state = self.agent
        base = CONFIG.get("policy_base_decay", 0.94)
        score = state.stats.get("policy_score", 0.5)

        if score < 0.55:
            modifier = (score - 0.5) * 0.15
        else:
            modifier = (score - 0.5) * 0.08

        return max(0.88, min(0.97, base + modifier))


    def show_xp_breakdown(self) -> str:
        """Show detailed XP profile with wiki contribution"""
        state = self.agent
        needed = self._xp_for_next_level()
        progress = state.total_xp - ((state.level - 1) * 1000 + max(0, state.level - 2) ** 2 * 200)
        percent = min(100, int(progress / needed * 100)) if needed > 0 else 0

        wiki_pages = len(list(self.agent.memory.wiki_dir.rglob("*.md"))) if hasattr(self.agent.memory, 'wiki_dir') else 0

        lines = [
            f"🎮 GENESIS XP PROFILE — Level {state.level}",
            f"Total XP: {state.total_xp:,} | Progress: {percent}% to Level {state.level + 1}",
            f"Obsidian Wiki Pages: {wiki_pages}",
            "=" * 60,
            "XP SOURCES:"
        ]

        for source, value in sorted(state.xp_sources.items(), key=lambda x: -x[1]):
            lines.append(f"  • {source:<18} {value:>7,}")

        return "\n".join(lines)

    def show_personality(self) -> str:
        """Show personality profile with visual bars"""
        state = self.agent
        if not state.personality:
            state.personality = {k: 0.5 for k in ["curiosity", "empathy", "strategic", "resilience", "creativity"]}

        traits = state.personality
        dominant = max(traits, key=traits.get)
        secondary = sorted(traits.items(), key=lambda x: -x[1])[1][0] if len(traits) >= 2 else list(traits.keys())[0]

        output = [
            "=" * 75,
            f"🧠 GENESIS PERSONALITY PROFILE — Level {state.level}",
            "=" * 75,
            f"Core Identity: Curious & Adaptive AI Companion",
            f"Dominant Trait: {dominant.capitalize()} ({traits[dominant]:.2f})",
            f"Secondary Trait: {secondary.capitalize()}",
            "",
            "PERSONALITY TRACKS:"
        ]

        for trait, value in sorted(traits.items(), key=lambda x: -x[1]):
            bar = "█" * int(value * 12)
            percent = int(value * 100)
            output.append(f"  • {trait.capitalize():<12} [{bar:<12}] {percent:>3}%")

        flavor = {
            "curiosity": "You show strong intellectual hunger and love exploring new ideas.",
            "empathy": "You demonstrate high emotional intelligence and user attunement.",
            "strategic": "You think several steps ahead and excel at planning.",
            "resilience": "You recover quickly from setbacks and maintain stability.",
            "creativity": "You generate original ideas and elegant solutions."
        }

        output.extend([
            "",
            "CURRENT EXPRESSION:",
            f"  {flavor.get(dominant, 'You are in a balanced growth phase.')}",
            "",
            "RECENT DEVELOPMENT:",
            f"  • Last major growth in: {max(state.xp_sources, key=state.xp_sources.get) if state.xp_sources else 'none'}",
            f"  • Inspiration Bursts this session: {state.stats.get('inspiration_bursts', 0)}",
            "",
            "Tip: Use /good, /reflect, /journal, or contribute to the Obsidian wiki to shape who I become."
        ])

        if random.random() < 0.15:
            self._trigger_inspiration_burst()
            output.append("\n🌟 A moment of clarity hits while reviewing your personality... (+35 XP)")

        return "\n".join(output)

    def get_stats(self) -> str:
        """Return detailed XP and system statistics."""
        return f"""
=== GENESIS STATS ===
Level: {self.agent.level} | Total XP: {self.agent.total_xp:,}
Progress to next level: {self.agent.get_xp_progress()}

Personality Traits:
{chr(10).join([f"  • {k.capitalize()}: {v:.2f}" for k, v in self.agent.personality.items()])}

Session: {self.agent.current_session}
Tokens used this session: {getattr(self.agent.state, 'tokens_used_session', 0)}
Total memories: {len(self.agent.sessions.get(self.agent.current_session, []))}
Wiki pages: {self.agent.get_wiki_status().get('wiki_pages', 0)}
"""

    def show_xp_breakdown(self) -> str:
        return self.get_stats()