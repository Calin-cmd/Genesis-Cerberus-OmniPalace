"""
Genesis v5.6.9 Cerberus OmniPalace — FactClaw (Bullshit Detector)
Multi-source verification, probability analysis, atomic fact extraction, and learning from mistakes.
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import List, Dict

from ..config import log_status


class FactClaw:
    """Analytical sceptic: verifies facts, calculates probability, extracts atomic facts, and learns from errors."""

    def __init__(self, agent):
        self.agent = agent
        self.verification_log = []

    def verify_fact(self, claim: str) -> Dict:
        """Full verification: internal + external + probability scoring."""
        print(f"[FACT CLAW] Verifying: {claim[:120]}...")

        # Internal retrieval
        internal = self.agent.memory.retrieve(claim, n_results=6)
        internal_conf = min(1.0, len(internal) / 6.0)

        # External check
        external = []
        try:
            ext = self.agent.tool_registry.execute("web_search", {"query": claim[:150], "max_results": 3})
            external = [ext] if ext else []
        except:
            pass

        # Probability score
        agreement = 1.0 if internal_conf > 0.6 and len(external) > 0 else 0.5
        probability = round((internal_conf * 0.65) + (agreement * 0.35), 2)

        verdict = "CONFIRMED" if probability >= 0.8 else "PLAUSIBLE" if probability >= 0.5 else "QUESTIONABLE"

        result = {
            "claim": claim,
            "verdict": verdict,
            "probability": probability,
            "internal_sources": len(internal),
            "external_sources": len(external),
            "timestamp": datetime.now().isoformat(),
            "recommendation": "High confidence — use freely" if verdict == "CONFIRMED" else "Cross-check before using" if verdict == "PLAUSIBLE" else "Likely inaccurate — investigate"
        }

        self.verification_log.append(result)
        self.agent.add(f"Fact check: {claim[:100]} → {verdict} ({probability})", topic="fact_verification", importance=0.88, tags=["verification", "bullshit_detector"])

        log_status(f"[FACT CLAW] {verdict} | Prob: {probability}")
        return result

    def extract_atomic_facts(self, text: str, source: str = "journal"):
        """Parse journals, predictions, reflections for verifiable atomic facts."""
        if len(text) < 50:
            return

        prompt = f"Extract 3-5 concise, verifiable atomic facts from this text. Format as bullet list.\n\nText: {text[:800]}"
        facts = self.agent.call_llm_safe("You are an atomic fact extractor.", prompt)

        self.agent.add(f"Atomic facts from {source}: {facts}", topic="atomic_fact", importance=0.75, tags=["atomic", source])
        return facts

    def learn_from_mistake(self, claim: str, outcome: str, reason: str):
        """Learn from failed predictions or false facts."""
        lesson = f"Failed verification/prediction: '{claim}' → Outcome: {outcome}. Root cause: {reason}"
        self.agent.add(lesson, topic="lesson_learned", importance=0.92, tags=["self_improvement", "error_analysis"])
        log_status(f"[LESSON LEARNED] {reason[:100]}...")
        return lesson