"""
Genesis v5.6.9 Cerberus OmniPalace — OnboardingManager
Full guided onboarding for primary users with personality bootstrapping.
"""

from __future__ import annotations
import getpass
import hashlib
import json
from datetime import datetime
from typing import Dict
from pathlib import Path

from ..config import log_status


class OnboardingManager:
    """Handles full user onboarding and personality bootstrapping."""

    def __init__(self, agent):
        self.agent = agent  # Avoid importing AgentMemory here to prevent circular import

    def is_first_run(self) -> bool:
        """Check if primary user has been onboarded."""
        registry_path = Path(self.agent.memory.get_memory_path("registry_wing"))
        return not (registry_path / "primary_user.json").exists()

    def run_onboarding(self, is_first_run: bool = False) -> str:
        """Full interactive onboarding experience."""
        print("\n" + "="*60)
        print("🌟 GENESIS ONBOARDING")
        print("="*60)

        if is_first_run:
            print("Welcome! Let's create your personal Genesis instance.\n")

        # Step 1: Name
        name = input("What is your preferred name? ").strip()
        if not name:
            name = "Primary User"

        # Step 2: Password
        print("\n🔐 System commands will be password-protected.")
        while True:
            password = getpass.getpass("Create password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password == confirm and len(password) >= 4:
                break
            print("❌ Passwords don't match or are too short. Try again.")

        # Step 3: Quick questions
        print("\nA few questions to understand you better:")
        hobby = input("One hobby or interest? ").strip() or "none specified"
        goal = input("One goal you'd like help with? ").strip() or "general assistance"

        # Step 4: Name for Genesis
        genesis_name = input("\nWhat would you like to call me? (Enter for 'Genesis'): ").strip() or "Genesis"

        # Step 5: Personality
        print("\nChoose my personality traits (comma-separated):")
        print("curious, empathetic, humorous, direct, strategic, creative, calm, witty, analytical")
        traits_input = input("Your choices: ").strip().lower()
        personality = [t.strip() for t in traits_input.split(",") if t.strip()]

        if not personality:
            personality = ["curious", "empathetic", "strategic"]

        # Save profile
        profile = {
            "display_name": name,
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "hobby": hobby,
            "goal": goal,
            "genesis_name": genesis_name,
            "personality_traits": personality,
            "onboarded_at": datetime.now().isoformat(),
            "trust_level": 1.0,
            "role": "primary"
        }

        registry_path = Path(self.agent.memory.get_memory_path("registry_wing")) / "primary_user.json"
        registry_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")

        # Update agent
        self.agent.user_name = name
        self.agent.genesis_name = genesis_name
        self.agent.personality_traits = personality

        self.agent.mark_dirty()

        log_status(f"[ONBOARDING] Completed for {name} | Genesis: {genesis_name}")

        return f"""
✅ Onboarding complete!

Welcome, {name}!
I am now **{genesis_name}** with your chosen traits: {', '.join(personality)}

You can re-run this anytime with `/onboarding`.
System commands are now password-protected.
Let's build something great together.
"""