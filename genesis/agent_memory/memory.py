"""
Genesis v5.6.9 Cerberus OmniPalace — MemoryManager
Manages all memory operations: ChromaDB, hybrid retrieval, caching, and integration with MemoryIndex.
Graph-aware RAG + full Obsidian-ready self-maintaining wiki vault.
"""

from __future__ import annotations
import random
import time
import hashlib
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from ..config import CONFIG, STORAGE_DIR, HAS_CHROMA, log_status
from .core import AgentMemory


class WikiManager:
    """Centralized Obsidian Vault manager."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent
        self.vault_dir = STORAGE_DIR / "obsidian_vault"
        self.raw_dir = self.vault_dir / "raw"
        self.wiki_dir = self.vault_dir / "wiki"
        self.indexes_dir = self.vault_dir / "indexes"
        self.attachments_dir = self.vault_dir / "attachments"

        for d in [self.vault_dir, self.raw_dir, self.wiki_dir, self.indexes_dir, self.attachments_dir]:
            d.mkdir(parents=True, exist_ok=True)

        (self.wiki_dir / "concepts").mkdir(exist_ok=True)
        (self.wiki_dir / "people").mkdir(exist_ok=True)
        (self.wiki_dir / "papers").mkdir(exist_ok=True)
        (self.wiki_dir / "projects").mkdir(exist_ok=True)
        (self.wiki_dir / "daily").mkdir(exist_ok=True)

        self._wiki_page_cache = None
        self._last_cache_time = 0

    def _invalidate_cache(self):
        self._wiki_page_cache = None

    def count_wiki_pages(self) -> int:
        now = time.time()
        if self._wiki_page_cache is None or now - self._last_cache_time > 30:
            self._wiki_page_cache = len(list(self.wiki_dir.rglob("*.md")))
            self._last_cache_time = now
        return self._wiki_page_cache

    def compile_vault(self, source_folder: Optional[str] = None) -> str:
        target = Path(source_folder) if source_folder else self.raw_dir
        if not target.exists():
            return f"Source folder {target} not found."

        processed = 0
        for file in target.rglob("*"):
            if file.is_file() and not file.name.startswith("."):
                try:
                    self._process_raw_file(file)
                    processed += 1
                except Exception as e:
                    print(f"[WikiManager] Failed {file.name}: {e}")

        self._generate_master_index()
        self._invalidate_cache()
        log_status(f"[OBSIDIAN] Compiled {processed} files")
        return f"✅ Obsidian vault compiled — {processed} files processed."

    def _process_raw_file(self, file_path: Path):
        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        rel_path = str(file_path.relative_to(self.raw_dir)) if self.raw_dir in file_path.parents else file_path.name

        if file_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.pdf'}:
            vision = self.agent.call_llm_safe(
                "You are a precise vision analysis agent.",
                f"Describe this file for the knowledge wiki: {file_path.name}"
            )
            content = f"# {title}\n\n{vision}"
        else:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        frontmatter = f"""---
title: "{title}"
created: {datetime.now().isoformat()}
updated: {datetime.now().isoformat()}
tags: [graphify, {file_path.suffix[1:]}]
source: "{rel_path}"
aliases: ["{title.lower()}"]
---

"""
        wiki_path = self.wiki_dir / f"{title.replace(' ', '_')}.md"
        wiki_path.write_text(frontmatter + content, encoding="utf-8")

        self.agent.index.add_graph_node(title, title, "document")
        self.agent.add(f"Wiki page: {title}", topic="wiki", importance=0.82, tags=["obsidian"])

    def _generate_master_index(self):
        index_path = self.wiki_dir / "index.md"
        content = f"""# Genesis Knowledge Wiki
**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Maps of Content
- [[Concepts]]
- [[People]]
- [[Papers]]
- [[Projects]]

## Recent Daily Notes
"""
        for daily in sorted((self.wiki_dir / "daily").glob("*.md"), reverse=True)[:7]:
            content += f"- [[{daily.stem}]]\n"
        index_path.write_text(content, encoding="utf-8")

    def heal(self, depth: str = "light") -> str:
        print(f"[WikiManager] Starting {depth.upper()} healing cycle...")
        result = self.agent.cerberus.run_with_context(
            "Scan the wiki for gaps, contradictions, or stale information and suggest fixes."
        )
        if depth == "full":
            self.agent.tool_registry.execute("web_search", {"query": "latest AI agent developments 2026"})
        self._invalidate_cache()
        return f"✅ Wiki healed ({depth} mode). {result[:300]}..."

    def get_status(self) -> dict:
        return {
            "wiki_pages": self.count_wiki_pages(),
            "raw_files": len(list(self.raw_dir.rglob("*"))) if self.raw_dir.exists() else 0,
            "vault_path": str(self.vault_dir)
        }


class MemoryManager:
    """Manages all memory operations: ChromaDB, MemoryIndex, hybrid retrieval, caching, and Obsidian Vault."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent
        self.chroma_client = None
        self.collection = None
        self._recent_rag_cache: Dict = {}

        # Transcript directory
        self.transcript_dir = STORAGE_DIR / "transcripts"
        self.transcript_dir.mkdir(parents=True, exist_ok=True)

        # ====================== Obsidian Vault ======================
        self.vault_dir = STORAGE_DIR / "obsidian_vault"
        self.raw_dir = self.vault_dir / "raw"
        self.wiki_dir = self.vault_dir / "wiki"
        self.indexes_dir = self.vault_dir / "indexes"
        self.attachments_dir = self.vault_dir / "attachments"
        
        for d in [self.vault_dir, self.raw_dir, self.wiki_dir, self.indexes_dir, self.attachments_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Create standard Obsidian folder structure
        (self.wiki_dir / "concepts").mkdir(exist_ok=True)
        (self.wiki_dir / "people").mkdir(exist_ok=True)
        (self.wiki_dir / "papers").mkdir(exist_ok=True)
        (self.wiki_dir / "projects").mkdir(exist_ok=True)
        (self.wiki_dir / "daily").mkdir(exist_ok=True)

        # Wiki Manager
        self.wiki = WikiManager(agent)

    def _init_chroma(self):
        """Initialize ChromaDB vector store"""
        if not HAS_CHROMA:
            print("[MEMORY] ChromaDB not installed — vector memory disabled")
            return

        try:
            import chromadb
            from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

            ef = OllamaEmbeddingFunction(
                model_name=CONFIG["ollama_embedding_model"],
                url=CONFIG["ollama_url"]
            )

            self.chroma_client = chromadb.PersistentClient(str(STORAGE_DIR / "chroma"))
            self.collection = self.chroma_client.get_or_create_collection(
                name="agent_memories",
                embedding_function=ef
            )
            print(f"[CHROMA] Ready — {self.collection.count()} memories")
        except Exception as e:
            print(f"[CHROMA ERROR] {e} — vector memory disabled")
            self.collection = None

    def _clean_caches(self):
        """Clean internal caches"""
        if len(self._recent_rag_cache) > 20:
            oldest = sorted(self._recent_rag_cache.items(), key=lambda x: x[1]["ts"])[:8]
            for k in [x[0] for x in oldest]:
                self._recent_rag_cache.pop(k, None)

        if hasattr(self.agent.index, '_evict_old_topic_cache'):
            self.agent.index._evict_old_topic_cache()

    def _hybrid_retrieve(self, query: str, n_results: int = 12) -> List[Dict]:
        """Hybrid retrieval: keyword (index) + vector (Chroma)"""
        results: List[Dict] = []
        query_lower = query.lower()

        for line in self.agent.index.index_lines[-300:]:
            if query_lower in line.lower():
                results.append({
                    "source": "index",
                    "content": line,
                    "importance": 0.6,
                    "distance": 0.0
                })
            if len(results) >= n_results * 2:
                break

        if self.collection:
            try:
                chroma_results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
                docs = chroma_results.get("documents", [[]])[0]
                metas = chroma_results.get("metadatas", [[]])[0]
                dists = chroma_results.get("distances", [[]])[0]

                for doc, meta, dist in zip(docs, metas, dists):
                    results.append({
                        "source": "chroma",
                        "content": doc,
                        "meta": meta,
                        "importance": meta.get("importance", 0.6),
                        "distance": dist
                    })
            except Exception as e:
                print(f"[Chroma Query Error] {e}")

        seen = set()
        unique = []
        for r in results:
            key = r.get("content", "")[:300]
            if key not in seen:
                seen.add(key)
                unique.append(r)

        unique.sort(key=lambda x: (-x.get("importance", 0.5), x.get("distance", 999)))
        return unique[:n_results]

    def retrieve(self, query: str, n_results: int = 4) -> List[Dict]:
        """Main public retrieval method — Graph-aware RAG"""
        n_results = min(n_results, 8)
        traditional = self.agent.index.retrieve(query, n_results * 2)
        
        # Graph-aware boost
        if hasattr(self.agent.index, 'graph_nodes') and self.agent.index.graph_nodes:
            for item in traditional:
                item["graph_boost"] = 0.0
                for node_id, node in self.agent.index.graph_nodes.items():
                    if node.get("label", "").lower() in item.get("content", "").lower():
                        item["graph_boost"] = 0.3
                        break
            traditional.sort(key=lambda x: (-x.get("importance", 0.5) - x.get("graph_boost", 0.0), x.get("distance", 999)))
        
        return traditional[:n_results]

    def add(self, content: str, topic: str = "general", importance: float = 0.6, tags: List[str] = None):
        """Add memory with novelty filtering — QUIET VERSION (no console spam)"""
        if not content or not content.strip():
            return None

        tags = tags or []

        # Novelty check via OmniPalace
        novelty = self.agent.omnipalace.compute_novelty(content)
        if novelty < CONFIG.get("novelty_threshold", 0.38) and random.random() < 0.65:
            return None

        final_importance = max(importance, 0.6 + novelty * 0.3)

        entry_id = self.agent.index.add_entry(
            content.strip(),
            topic,
            final_importance,
            tags
        )

        # Only log high-importance additions to keep console clean
        if entry_id and final_importance > 0.75:
            log_status(f"[MEMORY] Added → {topic} | imp={final_importance:.3f} | novelty={novelty:.2f}")

        if self.collection:
            try:
                self.collection.add(
                    documents=[content.strip()],
                    metadatas=[{"topic": topic, "importance": final_importance, "tags": ",".join(tags)}],
                    ids=[entry_id]
                )
            except Exception as e:
                print(f"[CHROMA ADD] Warning: {e}")

        self.agent.mark_dirty()
        return entry_id

    def ingest_folder(self, folder_path: str, mode: str = "standard") -> dict:
        """Phase 3/4: Graphify-style ingestion with Tree-sitter + Vision + SHA256 caching.
        Now supports Obsidian mode via mode='obsidian'."""
        if mode == "obsidian" or "obsidian" in str(folder_path).lower():
            return {"success": True, "message": self.compile_obsidian_vault(folder_path)}

        # === Original Graphify logic ===
        folder = Path(folder_path).resolve()
        if not folder.exists() or not folder.is_dir():
            return {"success": False, "error": "Folder does not exist or is not a directory"}

        processed = 0
        code_files = 0
        image_files = 0

        for file in folder.rglob("*"):
            if file.is_file() and not file.name.startswith("."):
                try:
                    rel_path = str(file.relative_to(folder))
                    file_type = file.suffix.lower()

                    raw_content = file.read_bytes()
                    file_hash = hashlib.sha256(raw_content).hexdigest()

                    if rel_path in self.agent.index.sha256_cache and self.agent.index.sha256_cache[rel_path] == file_hash:
                        continue

                    content = None

                    # Code files - Tree-sitter AST
                    if file_type in {'.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs', '.c', '.cs'}:
                        try:
                            from tree_sitter_languages import get_parser
                            lang = file_type[1:] if file_type != '.py' else 'python'
                            parser = get_parser(lang)
                            tree = parser.parse(raw_content)
                            content = f"File: {file.name}\nLanguage: {lang}\nAST Nodes: {tree.root_node.child_count}\n\n{raw_content.decode('utf-8', errors='ignore')[:1500]}"
                            code_files += 1
                        except Exception:
                            content = raw_content.decode('utf-8', errors='ignore')[:1500]

                    # Images / PDFs - Vision
                    elif file_type in {'.png', '.jpg', '.jpeg', '.webp', '.pdf'}:
                        try:
                            vision_result = self.agent.call_llm_safe(
                                "You are a precise vision analysis agent. Describe the image or document in detail, extract any visible text, and identify key concepts and relationships.",
                                f"Analyze this file: {file.name}"
                            )
                            content = f"Image/Document: {file.name}\nVision Analysis:\n{vision_result}"
                            image_files += 1
                        except Exception:
                            content = raw_content.decode('utf-8', errors='ignore')[:1000]

                    else:
                        content = raw_content.decode('utf-8', errors='ignore')[:1500]

                    if content:
                        tags = ["graphify", file_type[1:]] if file_type else ["graphify"]
                        self.agent.omnipalace.add_atomic(
                            f"Path: {rel_path}\n{content}",
                            tags=tags
                        )
                        self.agent.index.update_sha256(rel_path, file_hash)
                        processed += 1

                except Exception:
                    continue

        summary = self.agent.cerberus.run_with_context(
            f"Summarize the key concepts, architecture, important relationships, and overall structure from the ingested folder: {folder}"
        )

        self.agent.mark_dirty()
        return {
            "success": True,
            "files_processed": processed,
            "code_files": code_files,
            "image_files": image_files,
            "summary": summary[:600],
            "folder": str(folder)
        }

    # ====================== OBSIDIAN VAULT METHODS ======================

    def compile_obsidian_vault(self, source_folder: Optional[str] = None) -> str:
        """Wiki compilation: raw → clean, richly linked Obsidian wiki"""
        return self.wiki.compile_vault(source_folder)

    def _process_raw_file_to_wiki(self, file_path: Path):
        """Convert any raw file into a clean Markdown wiki page with YAML frontmatter"""
        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        rel_path = str(file_path.relative_to(self.raw_dir)) if self.raw_dir in file_path.parents else file_path.name

        if file_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.pdf'}:
            vision = self.agent.call_llm_safe(
                "You are a precise vision analysis agent.",
                f"Describe this file for the knowledge wiki: {file_path.name}"
            )
            content = f"# {title}\n\n{vision}"
        else:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        frontmatter = f"""---
title: "{title}"
created: {datetime.now().isoformat()}
updated: {datetime.now().isoformat()}
tags: [graphify, {file_path.suffix[1:]}]
source: "{rel_path}"
aliases: ["{title.lower()}"]
---

"""

        wiki_path = self.wiki_dir / f"{title.replace(' ', '_')}.md"
        wiki_path.write_text(frontmatter + content, encoding="utf-8")

        self.agent.index.add_graph_node(title, title, "document")
        self.agent.add(f"Wiki page: {title}", topic="wiki", importance=0.82, tags=["obsidian"])

    def _generate_master_index(self):
        """Create / update the main index.md with dynamic links"""
        index_path = self.wiki_dir / "index.md"
        content = f"""# Genesis Knowledge Wiki
**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Maps of Content
- [[Concepts]]
- [[People]]
- [[Papers]]
- [[Projects]]

## Recent Daily Notes
"""
        for daily in sorted((self.wiki_dir / "daily").glob("*.md"), reverse=True)[:7]:
            content += f"- [[{daily.stem}]]\n"

        index_path.write_text(content, encoding="utf-8")

    def heal_wiki(self, depth: str = "light") -> str:
        """Self-healing loop"""
        return self.wiki.heal(depth)

    def search(self, query: str) -> str:
        """Public search across memories + transcripts + Obsidian wiki"""
        results = self.agent.index.search(query)

        transcript_hits = []
        if self.transcript_dir.exists():
            for transcript in self.transcript_dir.glob("*.jsonl"):
                try:
                    content = transcript.read_text(encoding="utf-8")
                    if query.lower() in content.lower():
                        hit = content[content.lower().find(query.lower())-40:][:160]
                        transcript_hits.append(f"Transcript {transcript.name}: ...{hit}...")
                except:
                    pass

        output = [f"🔍 Search results for '{query}' ({len(results) + len(transcript_hits)} hits):"]
        for r in results[:10]:
            output.append(f"[{r.get('source', 'index')}] {r.get('content', '')[:320]}")
        output.extend(transcript_hits[:6])

        return "\n".join(output)

    def ensure_session_tracking(self, sess: str):
        """Ensure session exists in tracking dicts — uses delegation"""
        if sess not in self.agent.sessions:
            self.agent.sessions[sess] = []
        if sess not in self.agent.session_turn_count:
            self.agent.session_turn_count[sess] = 0
        if sess not in self.agent.turns_since_last_journal:
            self.agent.turns_since_last_journal[sess] = 0

    def _auto_prune_old_sessions(self):
        """Prune old sessions based on config"""
        if not CONFIG.get("auto_prune_enabled"):
            return

        cutoff = datetime.now() - timedelta(days=CONFIG.get("max_session_age_days", 30))
        to_delete = []

        for sess_name in list(self.agent.sessions.keys()):
            if sess_name.startswith("20") and len(sess_name) >= 10:
                try:
                    sess_date = datetime.strptime(sess_name[:10], "%B %d, %Y")
                    if sess_date < cutoff:
                        to_delete.append(sess_name)
                except:
                    pass

        for s in to_delete:
            self.agent.sessions.pop(s, None)

        if to_delete:
            print(f"[Prune] Removed {len(to_delete)} old sessions")
            self.agent.mark_dirty()

    def get_recent_context(self) -> str:
        """Helper for conversation context — uses delegated properties"""
        recent = self.agent.sessions.get(self.agent.current_session, [])[-10:]
        hist = "\n".join([
            f"User: {t.get('prompt','')} → Genesis: {t.get('response','')[:180]}"
            for t in recent
        ])
        memories = self.retrieve("current conversation", 3)
        
        mem_str = "\n".join([
            f"[{m.get('topic','general')}]: {m.get('content','')[:220]}" 
            for m in memories
        ]) if memories else "None retrieved"
        
        return f"HISTORY:\n{hist}\n\nMEMORIES / WIKI:\n{mem_str}"

    def get_stats(self) -> str:
        """Simple stats helper"""
        chroma_count = self.collection.count() if self.collection else 0
        wiki_count = self.wiki.count_wiki_pages()
        return f"Memories (index): {len(self.agent.index.index_lines)} | Chroma: {chroma_count} | Wiki pages: {wiki_count}"

    def cleanup_old_memories(self) -> int:
        """Delegate to index for low-importance archival"""
        return self.agent.index.cleanup_old_memories() if hasattr(self.agent.index, 'cleanup_old_memories') else 0

    def compile_obsidian_vault(self, source_folder: Optional[str] = None) -> str:
        return self.wiki.compile_vault(source_folder)

    def heal_wiki(self, depth: str = "light") -> str:
        return self.wiki.heal(depth)

    def get_wiki_status(self) -> dict:
        return self.wiki.get_status()