"""
Genesis v5.6.9 Cerberus OmniPalace — UserModelManager
User profile and preference tracking. Learns user name, preferences,
and style dynamically.
"""

from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path

from ..config import USER_MODEL_PATH, CONFIG
from .core import AgentMemory


class UserModelManager:
    """User profile and preference tracking"""

    def __init__(self, agent: AgentMemory):
        self.agent = agent
        self.user_name = ""  # Will be learned dynamically

    def load_user_model(self) -> dict:
        """Load user model from disk with safe defaults"""
        if USER_MODEL_PATH.exists():
            try:
                model = json.loads(USER_MODEL_PATH.read_text(encoding="utf-8"))
                if model.get("name"):
                    self.user_name = model["name"].strip()
                    # Sync to core immediately
                    if hasattr(self.agent, 'user_name'):
                        self.agent.user_name = self.user_name
                return model
            except Exception:
                pass
        
        # Default fresh model
        return {
            "name": self.user_name or "",
            "preferences": [],
            "interests": [],
            "communication_style": "",
            "projects": [],
            "location_context": "",
            "wiki_contributions": 0,
            "last_updated": datetime.now().isoformat(),
            "version": 1
        }

    def save_user_model(self, model: dict):
        """Save user model to disk"""
        model["last_updated"] = datetime.now().isoformat()
        USER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        USER_MODEL_PATH.write_text(json.dumps(model, indent=2), encoding="utf-8")

    def update_user_model(self, new_insights: str):
        if not CONFIG.get("user_model_enabled", True):
            return

        # === RESTORED ORIGINAL VISION: Force learning on every update ===
        # Always try to extract name/facts from recent context if not provided
        if not new_insights or len(new_insights.strip()) < 50:
            try:
                recent = "\n".join([
                    f"Turn {i}: {t.get('prompt','')[:300]} → {t.get('response','')[:200]}"
                    for i, t in enumerate(list(self.agent.sessions.values())[-5:], 1)
                    if t and isinstance(t, dict)
                ])
                if recent:
                    new_insights = recent
            except Exception:
                pass  # Fall back to original insights if anything fails

        model = self.load_user_model()

        update_prompt = f"""Current user model:
{json.dumps(model, indent=2)}

New conversation:
{new_insights}

Extract the REAL user's name ONLY if clearly stated ("my name is", "call me", "I'm [Name]", or direct correction).
NEVER set the name to "Genesis" or any AI name.
If a valid name is found, store it persistently.
Add any new preferences, interests, or projects.
Update communication style or location if observable.
Return ONLY valid JSON."""

        try:
            result = self.agent.call_llm_safe(
                "You are a precise user model updater. Protect the user's real identity. Never set user name to the AI's name.",
                update_prompt,
                model=CONFIG.get("rag_model")
            )
            
            json_match = re.search(r'(\{.*\})', result, re.DOTALL)
            if json_match:
                updated = json.loads(json_match.group(1))
                if updated.get("name") and "genesis" not in updated["name"].lower():
                    new_name = updated["name"].strip()
                    if new_name and new_name != self.user_name:
                        self.user_name = new_name
                        if hasattr(self.agent, 'user_name'):
                            self.agent.user_name = new_name
                        print(f"[USER MODEL] ✅ User name persistently set to: {new_name}")
                self.save_user_model(updated)
        except Exception as e:
            print(f"[USER MODEL] Update failed: {e}")

    def get_user_model_summary(self) -> str:
        """Return a short summary for system prompt with wiki awareness."""
        model = self.load_user_model()
        summary = []

        name = model.get("name", "").strip()
        if name:
            summary.append(f"User name: {name}")
        else:
            summary.append("User name: Unknown (still learning)")

        if model.get("preferences"):
            summary.append(f"Preferences: {', '.join(model['preferences'][:5])}")

        if model.get("interests"):
            summary.append(f"Interests: {', '.join(model['interests'][:4])}")

        if model.get("communication_style"):
            summary.append(f"Communication style: {model['communication_style']}")

        if model.get("location_context"):
            summary.append(f"Location context: {model['location_context']}")

        wiki_count = model.get("wiki_contributions", 0)
        if wiki_count > 0:
            summary.append(f"Wiki contributions: {wiki_count} pages")

        return "\n".join(summary) if summary else "User profile is still being learned."