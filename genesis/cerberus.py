"""
Genesis v5.6.9 Cerberus — CerberusOrchestrator
Multi-Agent Orchestrator: Researcher, Critic, Proposer, and Synthesizer.
Enhanced with Obsidian Wiki context.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import random

# Use full package import to avoid relative import issues when running directly
from genesis.config import CONFIG, log_status


class CerberusOrchestrator:
    """Cerberus Multi-Agent Orchestrator — Researcher, Critic, Proposer, Reflector.
    Now with Obsidian Wiki context for deeper knowledge synthesis."""

    def __init__(self, agent):
        self.agent = agent

    def run_with_context(self, context: str) -> str:
        """Main Cerberus reasoning pipeline with Wiki awareness."""
        if not CONFIG.get("cerberus_enabled", True):
            return self.agent.call_llm_safe(
                "You are Genesis. Give a direct, helpful, and concise response.",
                context
            )

        log_status("[CERBERUS MODE] Spawning 4 specialized agents...")

        try:
            # Add Wiki context hint when relevant
            wiki_hint = ""
            if hasattr(self.agent.memory, 'wiki') and self.agent.memory.wiki.count_wiki_pages() > 0:
                wiki_hint = "\n\nYou have access to a living Obsidian Wiki vault with compiled, interconnected knowledge. Reference it when appropriate for accuracy and depth."

            # Researcher
            research = self.agent.call_llm_safe(
                "You are a thorough Researcher agent. Gather facts and background." + wiki_hint,
                f"Research this topic thoroughly: {context}"
            )

            # Critic
            critique = self.agent.call_llm_safe(
                "You are a sharp Critic agent. Find weaknesses, gaps, and counterpoints." + wiki_hint,
                f"Critique this research and identify weaknesses: {research}"
            )

            # Proposer
            proposal = self.agent.call_llm_safe(
                "You are a creative Proposer agent. Suggest solutions and improvements." + wiki_hint,
                f"Based on this research and critique, propose solutions: {context}\nCritique: {critique}"
            )

            # Synthesizer
            final = self.agent.call_llm_safe(
                "You are the final Synthesizer agent. Combine everything into a clear, balanced, and useful answer." + wiki_hint,
                f"Research: {research}\nCritique: {critique}\nProposal: {proposal}\nOriginal query: {context}"
            )

            log_status("[CERBERUS] Synthesis complete")
            return final

        except Exception as e:
            log_status(f"[CERBERUS] Error, falling back to direct response: {e}")
            return self.agent.call_llm_safe(
                "You are Genesis. Give a direct, helpful, and concise response.",
                context
            )

    def spawn_agents(self, roles: List[str], task: str) -> List[str]:
        """Spawn multiple specialized agents"""
        responses = []
        for role in roles:
            resp = self.agent.call_llm_safe(
                f"You are a specialized {role} agent.",
                f"Task: {task}"
            )
            responses.append(resp)
        return responses


# Quick test
if __name__ == "__main__":
    print("CerberusOrchestrator loaded successfully.")