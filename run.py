#!/usr/bin/env python3
"""
Genesis v5.6.9 Cerberus OmniPalace
Production Main Entry Point
"""

import argparse
import sys
import threading
import signal
from pathlib import Path
import atexit

# Robust import setup
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from genesis.config import CONFIG, HELP_TEXT, log_status
from genesis.agent_memory.core import AgentMemory
from genesis.agent_memory.conversation import ConversationManager
from genesis.notification import ProactiveTools
from genesis.webhook import start_webhook_server
from genesis.voice import VoiceInterface
from genesis.agent_memory.api import create_api_app, run_api_server
from genesis.dependencies import HAS_FASTAPI


def signal_handler(sig, frame):
    """Graceful shutdown handler"""
    print("\n👋 Received shutdown signal. Saving state and stopping daemons...")
    # Daemons will be stopped via their stop() methods in the finally block
    sys.exit(0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genesis v5.6.9 Cerberus OmniPalace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--voice", action="store_true", help="Enable voice output")
    parser.add_argument("--no-daemons", action="store_true", help="Disable background daemons")
    parser.add_argument("--api", action="store_true", help="Start FastAPI server")
    parser.add_argument("--api-port", type=int, default=8000, help="FastAPI port")
    args = parser.parse_args()

    # Register graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("[GENESIS] Starting v5.6.9 Cerberus OmniPalace...")

    # Load agent with new persistence layer
    try:
        agent: AgentMemory = AgentMemory.load()
        wiki_count = agent.get_wiki_status().get("wiki_pages", 0)
        print(f"✅ Memory loaded successfully — Level {agent.level} | XP {agent.total_xp:,} | "
              f"User learned dynamically | Wiki pages: {wiki_count}")
    except Exception as e:
        print(f"[LOAD FAIL] {e} — Starting fresh instance")
        agent = AgentMemory()

    print("[Genesis] Persistent memory, OmniPalace, and Hall of Records fully active.")

    # Initialize conversation manager
    conversation = ConversationManager(agent)

    # Start background daemons unless disabled
    if not args.no_daemons:
        print("[DAEMONS] BackgroundSaver, AutoDream, and Scheduler started")
    else:
        print("[DAEMONS] Background daemons disabled by flag")

    print(f"[CORE] AgentMemory initialized — Level {agent.level} | Tools: {len(agent.tool_registry.list_tools()) if hasattr(agent, 'tool_registry') else 0}")

    # Start webhook server in background
    try:
        webhook_thread = threading.Thread(target=start_webhook_server, daemon=True)
        webhook_thread.start()
        print("[WEBHOOK] Background server started")
    except Exception as e:
        print(f"[WEBHOOK] Failed to start: {e}")

    # Start FastAPI if requested
    api_thread = None
    if args.api and HAS_FASTAPI:
        try:
            api_thread = threading.Thread(
                target=run_api_server, 
                args=(agent, args.api_port), 
                daemon=True
            )
            api_thread.start()
            print(f"[API] FastAPI server starting on port {args.api_port}")
        except Exception as e:
            print(f"[API] Failed to start: {e}")

    print("\n" + "="*80)
    print("🌟 GENESIS v5.6.9 CERBERUS OmniPalace — Obsidian Wiki Mode ACTIVE")
    print("="*80)
    print(HELP_TEXT)
    print("="*80)

    turn_counter = 0

    try:
        while True:
            try:
                line = input("\n[User] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Shutting down gracefully...")
                break

            if not line:
                continue

            turn_counter += 1

            # /new handling with proper archiving
            if line == "/new":
                print("[SESSION] Archiving current session before reset...")
                if hasattr(agent.autonomous, '_create_journal_entry'):
                    agent.autonomous._create_journal_entry(force=True)
                archived = agent.memory.cleanup_old_memories() if hasattr(agent.memory, 'cleanup_old_memories') else 0
                print(f"[SESSION] Archived {archived} items")
                agent.reset_session(hard_reset=False)
                continue

            # Quick mode toggles
            if line == "/fast":
                CONFIG["quick_mode"] = True
                print("⚡ Quick Mode Enabled")
                continue
            elif line == "/full":
                CONFIG["quick_mode"] = False
                print("🧠 Full Mode Enabled")
                continue

            # Main response generation
            response = conversation.generate(line)
            if response:
                print(f"\nGenesis: {response}\n")

            # Voice output
            if (CONFIG.get("enable_voice") or args.voice) and hasattr(VoiceInterface, 'speak'):
                VoiceInterface.speak(response[:300])

            # Periodic save
            if turn_counter % 6 == 0 or line.startswith(('/good', '/wrong', '/important', '/journal', '/reflect', '/audit')):
                agent.save()
            else:
                agent.mark_dirty()

    finally:
        # Final shutdown actions
        print("[SHUTDOWN] Performing final save...")
        agent.save()
        if hasattr(agent.autonomous, '_create_journal_entry'):
            agent.autonomous._create_journal_entry(force=True)
        print("[SHUTDOWN] Genesis v5.6.9 shut down gracefully. Goodbye!")
    
    return 0

# === RESTORED ORIGINAL VISION: Graceful shutdown with final journal + archive ===
def graceful_shutdown():
    print("\n[SHUTDOWN] Genesis shutting down gracefully...")
    try:
        if hasattr(agent, 'autonomous'):
            print("[SHUTDOWN] Creating final journal entry...")
            agent.autonomous._create_journal_entry(force=True)
        if hasattr(agent, 'save'):
            print("[SHUTDOWN] Saving persistent state...")
            agent.save()
        print("[SHUTDOWN] Hall of Records archive complete. Goodbye.")
    except Exception as e:
        print(f"[SHUTDOWN] Error during final save: {e}")

atexit.register(graceful_shutdown)

if __name__ == "__main__":
    sys.exit(main())