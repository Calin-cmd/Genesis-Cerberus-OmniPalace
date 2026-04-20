"""
Genesis Social Graph & Relationship Intelligence
With Social Claw for automatic detection and updates.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class Relationship:
    user_id: str
    display_name: str
    relationship_type: str = "acquaintance"
    trust_level: float = 0.5
    last_interaction: str = ""
    interaction_count: int = 0
    notes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class SocialGraph:
    """Dynamic social graph with Social Claw auto-updates."""

    def __init__(self, agent):
        self.agent = agent
        self.relationships: Dict[str, Relationship] = {}
        self._sync_from_state()

    def _sync_from_state(self):
        saved = getattr(self.agent.state, 'social_graph', {})
        for uid, data in saved.items():
            self.relationships[uid] = Relationship(
                user_id=uid,
                display_name=data.get("display_name", uid),
                relationship_type=data.get("relationship_type", "friend"),
                trust_level=data.get("trust_level", 0.6),
                last_interaction=data.get("last_interaction", ""),
                interaction_count=data.get("interaction_count", 0),
                notes=data.get("notes", []),
                tags=data.get("tags", [])
            )

        if "default" not in self.relationships:
            self.relationships["default"] = Relationship(
                user_id="default",
                display_name="Primary User",
                relationship_type="primary",
                trust_level=1.0,
                last_interaction=datetime.now().isoformat(),
                interaction_count=999
            )

    def _sync_to_state(self):
        data = {}
        for uid, rel in self.relationships.items():
            data[uid] = {
                "display_name": rel.display_name,
                "relationship_type": rel.relationship_type,
                "trust_level": rel.trust_level,
                "last_interaction": rel.last_interaction,
                "interaction_count": rel.interaction_count,
                "notes": rel.notes,
                "tags": rel.tags
            }
        self.agent.state.social_graph = data
        self.agent.mark_dirty()

    def add_person(self, user_id: str, display_name: str, relationship_type: str = "friend", trust: float = 0.6):
        if user_id in self.relationships:
            rel = self.relationships[user_id]
            rel.display_name = display_name
            rel.relationship_type = relationship_type
            rel.trust_level = trust
        else:
            self.relationships[user_id] = Relationship(
                user_id=user_id,
                display_name=display_name,
                relationship_type=relationship_type,
                trust_level=trust,
                last_interaction=datetime.now().isoformat()
            )
        self._sync_to_state()
        return f"✅ Added/updated {display_name} as {relationship_type} (Trust: {trust:.1f})"

    def record_interaction(self, user_id: str, note: str = "", context: str = ""):
        """Social Claw: Automatic interaction recording and trust adjustment."""
        if user_id not in self.relationships:
            return False

        rel = self.relationships[user_id]
        rel.last_interaction = datetime.now().isoformat()
        rel.interaction_count += 1
        if note:
            rel.notes.append(note)

        # Gentle trust updates based on context
        context_lower = context.lower()
        if any(word in context_lower for word in ["good", "thanks", "great", "love", "helpful", "positive"]):
            rel.trust_level = min(1.0, rel.trust_level + 0.03)
        elif any(word in context_lower for word in ["bad", "wrong", "frustrated", "angry"]):
            rel.trust_level = max(0.2, rel.trust_level - 0.02)

        self._sync_to_state()
        return True

    def list_social_circle(self) -> str:
        if not self.relationships:
            return "Social circle is empty."
        lines = ["**Social Circle:**"]
        for uid, rel in sorted(self.relationships.items(), key=lambda x: x[1].trust_level, reverse=True):
            active = "→ " if uid == getattr(self.agent.state, 'current_user_id', 'default') else "  "
            lines.append(f"{active}{rel.display_name} ({uid}) - {rel.relationship_type} | Trust: {rel.trust_level:.2f} | Interactions: {rel.interaction_count}")
        return "\n".join(lines)