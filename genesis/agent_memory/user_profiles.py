"""
Genesis Unified User Profile System
Persistent multi-user support with reliable context switching.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class UserProfile:
    user_id: str
    display_name: str
    trust_level: float = 0.8
    relationship_type: str = "friend"
    last_interaction: str = ""
    interaction_count: int = 0


class UserProfileManager:
    """Unified persistent multi-user manager."""

    def __init__(self, agent):
        self.agent = agent
        self.profiles: Dict[str, UserProfile] = {}
        self.current_user_id = "default"
        self._load_profiles()

    def _load_profiles(self):
        saved = getattr(self.agent.state, 'user_profiles', {})
        for uid, data in saved.items():
            self.profiles[uid] = UserProfile(
                user_id=uid,
                display_name=data.get("display_name", "User"),
                trust_level=data.get("trust_level", 0.7),
                relationship_type=data.get("relationship_type", "friend"),
                last_interaction=data.get("last_interaction", ""),
                interaction_count=data.get("interaction_count", 0)
            )

        if "default" not in self.profiles:
            self.profiles["default"] = UserProfile(
                user_id="default",
                display_name="Primary User",
                trust_level=1.0,
                relationship_type="primary",
                last_interaction=datetime.now().isoformat(),
                interaction_count=999
            )

    def _save_profiles(self):
        data = {}
        for uid, p in self.profiles.items():
            data[uid] = {
                "display_name": p.display_name,
                "trust_level": p.trust_level,
                "relationship_type": p.relationship_type,
                "last_interaction": p.last_interaction,
                "interaction_count": p.interaction_count
            }
        self.agent.state.user_profiles = data
        self.agent.mark_dirty()

    def switch_user(self, user_id: str) -> str:
        if user_id in self.profiles:
            self.current_user_id = user_id
            self.agent.state.current_user_id = user_id
            self.agent.mark_dirty()
            self._save_profiles()
            return f"👤 Switched to user: {self.profiles[user_id].display_name} (ID: {user_id})"
        return f"❌ User '{user_id}' not found. Use /users to list."

    def get_current_profile(self):
        return self.profiles.get(self.current_user_id, self.profiles.get("default"))

    def get_greeting(self) -> str:
        profile = self.get_current_profile()
        return f"Hello, {profile.display_name}! 👋"

    def add_user(self, user_id: str, display_name: str, relationship: str = "friend", trust: float = 0.7):
        self.profiles[user_id] = UserProfile(
            user_id=user_id,
            display_name=display_name,
            relationship_type=relationship,
            trust_level=trust,
            last_interaction=datetime.now().isoformat()
        )
        self._save_profiles()
        return f"✅ Added new user: {display_name} (Trust: {trust:.1f})"

    def list_users(self) -> str:
        lines = ["**Registered Users:**"]
        for uid, p in self.profiles.items():
            active = "→ " if uid == self.current_user_id else "  "
            lines.append(f"{active}{p.display_name} ({uid}) - Trust: {p.trust_level:.1f} - {p.relationship_type}")
        return "\n".join(lines)