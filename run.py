#!/usr/bin/env python3
"""
Genesis v5.6.9 Cerberus OmniPalace
Production Main Entry Point
"""

import argparse
import threading
import signal
from pathlib import Path
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

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
    print("\n👋 Received shutdown signal (Ctrl+C). Saving state...")
    graceful_shutdown()
    sys.exit(0)


def graceful_shutdown():
    print("\n👋 Received shutdown signal. Saving state and stopping daemons...")
    print("[SHUTDOWN] Performing final encrypted save...")

    try:
        if 'agent' in globals() and agent is not None:
            if hasattr(agent, 'autonomous') and hasattr(agent.autonomous, '_create_journal_entry'):
                try:
                    agent.autonomous._create_journal_entry(force=True)
                except:
                    pass
            agent.save()
            print("[SHUTDOWN] Final encrypted save completed.")
            print("[SHUTDOWN] Genesis v5.6.9 shut down gracefully. Goodbye!")
        else:
            print("[SHUTDOWN] No active agent found.")
    except Exception as e:
        print(f"[SHUTDOWN] Error during final save: {e}")

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

    # Load agent
    try:
        agent: AgentMemory = AgentMemory.load()
        wiki_count = agent.get_wiki_status().get("wiki_pages", 0)
        print(f"✅ Memory loaded successfully — Level {agent.level} | XP {agent.total_xp:,} | "
              f"User learned dynamically | Wiki pages: {wiki_count}")
    except Exception as e:
        print(f"[LOAD FAIL] {e} — Starting fresh instance")
        agent = AgentMemory()

    print("[Genesis] Persistent memory, OmniPalace, and Hall of Records fully active.")

    conversation = ConversationManager(agent)

    if not args.no_daemons:
        print("[DAEMONS] BackgroundSaver, AutoDream, and Scheduler started")
    else:
        print("[DAEMONS] Background daemons disabled by flag")

    print(f"[CORE] AgentMemory initialized — Level {agent.level} | Tools: {len(agent.tool_registry.list_tools()) if hasattr(agent, 'tool_registry') else 0}")

    # Start webhook server
    try:
        webhook_thread = threading.Thread(target=start_webhook_server, daemon=True)
        webhook_thread.start()

    except Exception as e:
        print(f"[WEBHOOK] Failed to start: {e}")

    # Start FastAPI if requested
    if args.api and HAS_FASTAPI:
        try:
            api_thread = threading.Thread(target=run_api_server, args=(agent, args.api_port), daemon=True)
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
        graceful_shutdown()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())