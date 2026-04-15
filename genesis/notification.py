"""
Genesis v5.6.9 Cerberus OmniPalace — Notification System
Secure notification logging and proactive tools.
Updated with Obsidian Wiki notifications.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import (
    STORAGE_DIR, NOTIFICATIONS_LOG, OUTBOUND_DIR, DAILY_TASK_LOG,
    SCHEDULED_TASKS, COMPLETED_TASKS, ALLOWED_ACTIONS, log_status
)
from .dependencies import HAS_PLYER


# ====================== SECURE NOTIFICATION LOGGER ======================
class SecureNotificationLogger:
    """Secure logging for all notifications with security scanning"""

    def __init__(self, log_file: str = "secure_notifications.json"):
        self.log_file = STORAGE_DIR / log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.notifications: list = self._load()
        
        self.suspicious_keywords = {
            "hack", "exploit", "password", "secret", "key", "token", "http", "url:",
            "rm -rf", "delete", "shutdown", "exec", "os.system", "subprocess", "eval",
            "base64", "powershell", "cmd.exe", "sudo", "shell", "injection", "rmdir",
            "format", "virus", "malware", "payload", "backdoor"
        }

    def _load(self) -> list:
        if self.log_file.exists():
            try:
                return json.loads(self.log_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self):
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(self.notifications[-500:], f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def log(self, title: str, msg: str = "", source: str = "system", action: str = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "title": title or "Notification",
            "message": msg,
            "source": source,
            "action": action,
            "security_status": "PASSED",
            "parsed_flags": []
        }

        text_lower = (title + " " + (msg or "")).lower()
        for kw in self.suspicious_keywords:
            if kw in text_lower:
                entry["security_status"] = "FLAGGED"
                entry["parsed_flags"].append(kw)

        self.notifications.append(entry)
        self._save()

        print(f" [NOTIFICATION] {title}")
        if msg:
            print(f"   {msg}")
        if entry["parsed_flags"]:
            print(f"    ⚠️ SECURITY FLAGS: {', '.join(entry['parsed_flags'])}")

        return entry


# ====================== PROACTIVE TOOLS ======================
class ProactiveTools:
    """Collection of proactive real-world tools with Obsidian Wiki support."""

    @staticmethod
    def push_notification(title: str, message: str, timeout: int = 8):
        """Send desktop notification"""
        if HAS_PLYER:
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message[:200],
                    timeout=timeout,
                    app_name="Genesis"
                )
            except Exception:
                pass
        
        print(f"\n[🔔 NOTIFICATION] {title}\n   {message}\n")

    @staticmethod
    def play_music(style: str = "jazz"):
        """Open Spotify playlist"""
        urls = {
            "jazz": "https://open.spotify.com/playlist/37i9dQZF1DX0SM0LQTn6da",
            "relax": "https://open.spotify.com/playlist/37i9dQZF1DX4sWSpwq3LiO",
            "focus": "https://open.spotify.com/playlist/37i9dQZF1DX8Fwnk5X6Z2V",
        }
        url = urls.get(style.lower(), urls["jazz"])
        try:
            import webbrowser
            webbrowser.open(url)
            ProactiveTools.push_notification("🎵 Music Started", f"Playing {style} on Spotify")
            return f"Music ({style}) started"
        except Exception as e:
            return f"Failed to start music: {e}"

    @staticmethod
    def send_file(filename: str, content: str):
        """Save generated content to outbound folder"""
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        filepath = OUTBOUND_DIR / safe_name
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            ProactiveTools.push_notification("📄 File Delivered", f"{filename} saved to outbound/")
            return str(filepath)
        except Exception as e:
            return f"Failed to save file: {e}"

    @staticmethod
    def schedule_action(delay_minutes: int, action: str, custom_prompt: str = None):
        """Schedule a future proactive action"""
        action_lower = action.lower().strip()
        
        if not any(word in action_lower for word in ALLOWED_ACTIONS):
            return f"Action '{action}' not allowed for security reasons."

        if custom_prompt is None:
            custom_prompt = f"Execute scheduled action: {action}"

        wakeup_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        task = {
            "id": str(uuid.uuid4()),
            "wakeup": wakeup_time.isoformat(),
            "action": action_lower,
            "custom_prompt": custom_prompt,
            "status": "pending"
        }

        try:
            with open(SCHEDULED_TASKS, "a", encoding="utf-8") as f:
                f.write(json.dumps(task) + "\n")
            
            ProactiveTools.push_notification("⏰ Scheduled", f"'{action}' in {delay_minutes} minutes")
            return f"Scheduled {action} for {wakeup_time.strftime('%H:%M')}"
        except Exception as e:
            return f"Failed to schedule action: {e}"

    @staticmethod
    def wiki_notification(message: str):
        """Special notification for Obsidian Wiki events"""
        ProactiveTools.push_notification("📖 Obsidian Wiki", message)


# For debugging
if __name__ == "__main__":
    print("Notification system loaded with Obsidian Wiki support.")