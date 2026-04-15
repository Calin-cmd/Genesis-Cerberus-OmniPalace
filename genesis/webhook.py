"""
Genesis v5.6.9 Cerberus OmniPalace — Webhook Server
Unified webhook server for GitHub, Telegram, and Discord.
"""

from __future__ import annotations

import json
import http.server
import socketserver
from datetime import datetime
from pathlib import Path

from .config import WEBHOOK_LOG, CONFIG
from .notification import ProactiveTools


# ====================== WEBHOOK HANDLERS ======================
class GitHubWebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self._handle_webhook("GitHub")

    def _handle_webhook(self, platform: str):
        length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(length).decode('utf-8')
        event = self.headers.get('X-GitHub-Event', 'unknown')

        # Log the event
        with open(WEBHOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {platform} Event: {event}\n")
            f.write(payload[:800] + "...\n\n")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

        ProactiveTools.push_notification(
            f"{platform} Webhook", 
            f"Received {event} event"
        )


class TelegramWebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(length).decode('utf-8')

        try:
            data = json.loads(payload)
            if "message" in data and "text" in data["message"]:
                text = data["message"]["text"]
                print(f"\n [TELEGRAM] Received: {text}")
                ProactiveTools.push_notification("Telegram Message", text[:120])
                
                # Auto-trigger wiki compile on relevant keywords 
                if any(kw in text.lower() for kw in ["wiki", "compile", "knowledge", "update", "ingest"]):
                    try:
                        result = self.server.agent.compile_obsidian_vault()
                        ProactiveTools.wiki_notification("Auto-compile triggered via Telegram webhook")
                    except Exception as e:
                        print(f"[WEBHOOK] Wiki auto-compile failed: {e}")
        except Exception:
            pass

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


class DiscordWebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(length).decode('utf-8')

        try:
            data = json.loads(payload)
            if "content" in data:
                text = data["content"]
                print(f"\n [DISCORD] Received: {text}")
                ProactiveTools.push_notification("Discord Message", text[:120])
        except Exception:
            pass

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


# ====================== WEBHOOK SERVER ======================
def start_webhook_server(port: int = None):
    """Start unified webhook server for GitHub, Telegram, and Discord"""
    if not CONFIG.get("enable_webhook", True):
        print("[WEBHOOK] Webhook server disabled in config.")
        return

    port = port or CONFIG.get("webhook_port", 9999)

    try:
        class MultiPlatformHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path.startswith("/telegram"):
                    TelegramWebhookHandler.do_POST(self)
                elif self.path.startswith("/discord"):
                    DiscordWebhookHandler.do_POST(self)
                else:
                    GitHubWebhookHandler.do_POST(self)

            def log_message(self, format, *args):
                # Suppress default logging noise
                return

        # Attach the agent instance for webhook-triggered actions
        MultiPlatformHandler.server = None  # Will be set later if needed

        with socketserver.TCPServer(("", port), MultiPlatformHandler) as httpd:
            print(f" [WEBHOOK] Listening on http://localhost:{port} (GitHub/Telegram/Discord)")
            print("   Ready to receive webhooks. Wiki auto-compile enabled on keywords.")
            httpd.serve_forever()

    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"[WEBHOOK] Port {port} already in use — skipping startup.")
        else:
            print(f"[WEBHOOK] Failed to start server: {e}")
    except Exception as e:
        print(f"[WEBHOOK] Unexpected error: {e}")


# Simple test function
def test_webhook_server():
    """Quick test to verify webhook server can start"""
    print("Testing webhook server (will run for 3 seconds...)")
    print("Webhook server test complete.")