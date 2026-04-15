"""
Genesis v5.6.9 Cerberus OmniPalace — Advanced RAG
Advanced Retrieval-Augmented Generation helpers (HyDE, reranking, etc.).
Now deeply integrated with Obsidian Wiki knowledge retrieval.
Enhanced to better surface recent journals and important memories.
"""

from __future__ import annotations

from typing import List, Dict

from ..config import CONFIG, RAG_MODEL
from ..utils import dump_trace


# ====================== ADVANCED RAG ======================
class AdvancedRAG:
    """Advanced Retrieval-Augmented Generation helpers with Obsidian Wiki priority."""

    @staticmethod
    def hyde_query(state: "AgentMemory", original_query: str) -> str:
        """Hypothetical Document Embedding (HyDE) — generates a hypothetical answer first"""
        if not CONFIG.get("hyde_enabled") or not CONFIG.get("enable_full_rag"):
            return original_query
        
        prompt = f"Given this user query, write a short hypothetical perfect answer that would be highly relevant:\n\n{original_query}"
        
        try:
            hyde_answer = state.call_llm_safe(
                "You are a precise hypothetical answer generator.", 
                prompt, 
                model=RAG_MODEL
            )
            dump_trace("hyde_generated", {
                "original_query": original_query[:100],
                "hyde_answer": hyde_answer[:150]
            })
            return hyde_answer[:400]
        except Exception as e:
            print(f"[HYDE] Failed: {e} — falling back to original query")
            return original_query

    @staticmethod
    def retrieve_with_parent(state: "AgentMemory", query: str, n_results: int = 4) -> List[Dict]:
        """Enhanced retrieval with HyDE + parent context + Obsidian Wiki priority + recent journals boost."""
        if not CONFIG.get("enable_full_rag"):
            return []
        
        # Use HyDE to improve retrieval quality
        enhanced_query = AdvancedRAG.hyde_query(state, query)
        
        # Prioritize Obsidian Wiki results
        wiki_results = []
        if hasattr(state.memory, 'wiki_dir'):
            try:
                for md_file in state.memory.wiki_dir.rglob("*.md"):
                    try:
                        content = md_file.read_text(encoding="utf-8", errors="ignore")
                        if query.lower() in content.lower() or enhanced_query.lower() in content.lower():
                            wiki_results.append({
                                "source": "obsidian_wiki",
                                "content": f"Wiki Page: {md_file.name}\n{content[:600]}...",
                                "importance": 0.92,
                                "distance": 0.0
                            })
                    except:
                        continue
            except:
                pass

        # Standard retrieval from index
        candidates = state.index.retrieve(enhanced_query, n_results * 2)
        
        # Boost recent journals and reflections
        for item in candidates:
            content_lower = item.get("content", "").lower()
            if any(kw in content_lower for kw in ["journal", "reflection", "audit"]):
                item["importance"] = item.get("importance", 0.5) + 0.35

        # Combine and prioritize
        all_results = wiki_results + candidates
        all_results = sorted(
            all_results, 
            key=lambda x: (-x.get("importance", 0.5), x.get("distance", 999))
        )
        
        return all_results[:n_results]

    @staticmethod
    def rerank_results(results: List[Dict], query: str) -> List[Dict]:
        """Rerank results with bonus for Obsidian Wiki pages and recent journals."""
        if not results:
            return []
            
        # Boost wiki and journal results
        for r in results:
            source = r.get("source", "")
            content = r.get("content", "").lower()
            if source == "obsidian_wiki":
                r["importance"] = r.get("importance", 0.5) + 0.28
            elif any(kw in content for kw in ["journal", "reflection", "audit"]):
                r["importance"] = r.get("importance", 0.5) + 0.22
        
        return sorted(
            results, 
            key=lambda x: x.get("importance", 0.5), 
            reverse=True
        )