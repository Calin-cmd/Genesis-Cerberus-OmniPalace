"""
Genesis Access Control & Authentication Manager
Handles onboarding, passwords, timeouts, command whitelisting, and User Detect Claw.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib

from ..config import CONFIG
from ..security.encryption import secure_storage


@dataclass
class AccessProfile:
    user_id: str
    display_name: str
    is_primary: bool = False
    password_hash: str = ""
    timeout_minutes: int = 30          # 0 = never timeout
    last_auth: str = ""
    granted_system_access: List[str] = field(default_factory=list)  # "all" or specific commands


class AccessControl:
    """Central authentication and command authorization subsystem."""

    def __init__(self, agent):
        self.agent = agent
        self.profiles: Dict[str, AccessProfile] = {}
        self.current_user_id = "default"
        self._load_profiles()

    def _load_profiles(self):
        saved = getattr(self.agent.state, 'access_profiles', {})
        for uid, data in saved.items():
            self.profiles[uid] = AccessProfile(
                user_id=uid,
                display_name=data.get("display_name", "User"),
                is_primary=data.get("is_primary", False),
                password_hash=data.get("password_hash", ""),
                timeout_minutes=data.get("timeout_minutes", 30),
                last_auth=data.get("last_auth", ""),
                granted_system_access=data.get("granted_system_access", [])
            )

        if "default" not in self.profiles:
            self.profiles["default"] = AccessProfile(
                user_id="default",
                display_name="Primary User",
                is_primary=True,
                timeout_minutes=0
            )

    def _save_profiles(self):
        data = {}
        for uid, p in self.profiles.items():
            data[uid] = {
                "display_name": p.display_name,
                "is_primary": p.is_primary,
                "password_hash": p.password_hash,
                "timeout_minutes": p.timeout_minutes,
                "last_auth": p.last_auth,
                "granted_system_access": p.granted_system_access
            }
        self.agent.state.access_profiles = data
        self.agent.mark_dirty()

    def onboard_primary(self, display_name: str, password: str) -> str:
        """Onboarding for the primary user."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.profiles["default"] = AccessProfile(
            user_id="default",
            display_name=display_name,
            is_primary=True,
            password_hash=password_hash,
            timeout_minutes=0
        )
        self._save_profiles()
        return f"✅ Primary user '{display_name}' onboarded successfully with password protection."

    def check_auth(self, user_id: str, provided_password: str = None) -> bool:
        """Check if user is authenticated."""
        if user_id not in self.profiles:
            return False
        profile = self.profiles[user_id]

        if profile.is_primary:
            return True

        if provided_password:
            if hashlib.sha256(provided_password.encode()).hexdigest() == profile.password_hash:
                profile.last_auth = datetime.now().isoformat()
                self._save_profiles()
                return True
        return False

    def is_system_command_allowed(self, user_id: str, command: str) -> bool:
        """Check if current user can run system commands."""
        if user_id not in self.profiles:
            return False
        profile = self.profiles[user_id]
        if profile.is_primary:
            return True
        if "all" in profile.granted_system_access:
            return True
        return command in profile.granted_system_access

    def grant_access(self, granter_id: str, target_id: str, command: str = "all", temporary_minutes: int = 0) -> str:
        """Primary user grants access to another user."""
        if granter_id != "default" or target_id not in self.profiles:
            return "Access denied."
        if command == "all":
            self.profiles[target_id].granted_system_access = ["all"]
        else:
            self.profiles[target_id].granted_system_access.append(command)
        self._save_profiles()
        return f"✅ Access granted to {target_id} for '{command}'."

    def set_timeout(self, minutes: int) -> str:
        """Set authentication timeout for current user."""
        if self.current_user_id in self.profiles:
            self.profiles[self.current_user_id].timeout_minutes = minutes
            self._save_profiles()
            return f"✅ Timeout set to {minutes} minutes."
        return "User not found."

    def get_current_user_display(self) -> str:
        profile = self.profiles.get(self.current_user_id, self.profiles.get("default"))
        return profile.display_name