"""
Genesis v5.6.9 Cerberus OmniPalace — Daemons
Background threads: ProactiveScheduler, AutoDreamDaemon, and BackgroundSaver.
Updated with Obsidian Wiki self-healing integration.
"""

from __future__ import annotations

import threading
import time
import random
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .config import (
    SCHEDULED_TASKS, COMPLETED_TASKS, SCHEDULER_LOCK, 
    log_status, CONFIG
)
from .notification import ProactiveTools

# Avoid circular import
if TYPE_CHECKING:
    from .core import AgentMemory


# ====================== DAEMONS ======================
class ProactiveScheduler(threading.Thread):
    """Background thread that checks and executes scheduled tasks"""

    def __init__(self, state: "AgentMemory"):
        super().__init__(daemon=True, name="ProactiveScheduler")
        self.state = state
        self.stop_event = threading.Event()
        self.start()

    def run(self):
        print("[SCHEDULER] ProactiveScheduler started")
        while not self.stop_event.is_set():
            time.sleep(15)
            self._check_due_tasks()

    def _check_due_tasks(self):
        if not SCHEDULED_TASKS.exists():
            return

        new_lines = []
        with SCHEDULER_LOCK:
            try:
                lines = SCHEDULED_TASKS.read_text(encoding="utf-8").splitlines()
            except Exception:
                return

            for line in lines:
                if not line.strip():
                    continue
                try:
                    task = json.loads(line.strip())
                    if (datetime.fromisoformat(task["wakeup"]) <= datetime.now() 
                        and task.get("status") == "pending"):
                        self._execute_proactive_task(task)
                    else:
                        new_lines.append(line)
                except Exception:
                    new_lines.append(line)

            try:
                tmp = SCHEDULED_TASKS.with_suffix(".tmp")
                tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                tmp.replace(SCHEDULED_TASKS)
            except Exception as e:
                print(f"[SCHEDULER] Failed to update: {e}")

    def _execute_proactive_task(self, task: dict):
        action = task["action"]
        custom_prompt = task.get("custom_prompt", f"Execute scheduled action: {action}")

        print(f"[SCHEDULER] Executing: {action}")

        result = self.state.call_llm_safe(
            "You are Genesis executing a scheduled proactive task.", 
            custom_prompt
        )

        ProactiveTools.push_notification(f"Scheduled: {action}", result[:180])

        self.state.index.add_entry(
            f"Scheduled task '{action}' completed: {result[:200]}", 
            topic="proactive_task", 
            importance=0.75
        )

        task["status"] = "completed"
        task["result"] = result
        task["completed_at"] = datetime.now().isoformat()

        with open(COMPLETED_TASKS, "a", encoding="utf-8") as f:
            f.write(json.dumps(task) + "\n")

    def stop(self):
        self.stop_event.set()


class AutoDreamDaemon(threading.Thread):
    """Background memory maintenance daemon with Wiki healing."""

    def __init__(self, state: "AgentMemory"):
        super().__init__(daemon=True, name="AutoDream")
        self.state = state
        self.stop_event = threading.Event()
        self.start()

    def run(self):
        print("[AUTODREAM] AutoDreamDaemon started")
        while not self.stop_event.is_set():
            time.sleep(random.uniform(240, 480))  # 4 to 8 minutes
            try:
                with self.state._lock():
                    self.state.autonomous._run_full_auto_dream()
            except Exception as e:
                log_status(f"[AUTODREAM] Error: {e}")

    def stop(self):
        self.stop_event.set()


class BackgroundSaver(threading.Thread):
    """Periodic background memory saver"""

    def __init__(self, state: "AgentMemory"):
        super().__init__(daemon=True, name="MemSaver")
        self.state = state
        self.stop_event = threading.Event()
        self.start()

    def run(self):
        print("[SAVER] BackgroundSaver started")
        while not self.stop_event.is_set():
            time.sleep(60 + random.uniform(-15, 20))
            try:
                saved = self.state.save_if_changed() if hasattr(self.state, 'save_if_changed') else False
                if saved:
                    log_status("[SAVER] Memory saved to disk")
            except Exception as e:
                print(f"[SAVER] Error: {e}")

    def stop(self):
        self.stop_event.set()