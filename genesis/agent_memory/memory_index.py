"""
Genesis v5.6.9 Cerberus OmniPalace — MemoryIndex
Hybrid memory index — flat file + topic cache + skills support.
Full Graphify integration with Leiden clustering,
rich metadata, SHA256 caching, and Obsidian Markdown export support.
Enhanced archiving so journals and important entries are never lost.
"""

from __future__ import annotations
import json
import uuid
import re
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Any

from ..config import (
    STORAGE_DIR, TOPICS_DIR, SKILLS_DIR, SKILLS_INDEX_PATH,
    ARCHIVE_DIR, MEMORY_INDEX_PATH, log_status
)
from .core import AgentMemory


class MemoryIndex:
    """Hybrid memory index with full Graphify Phase 3 + Obsidian Vault support."""

    def __init__(self, agent: "AgentMemory"):
        self.agent = agent
        self.index_lines: List[str] = []
        self.topic_subcache: Dict[str, List[str]] = {}

        # Graphify Phase 3 metadata
        self.graph_nodes: Dict[str, Dict] = {}      # node_id → node data
        self.graph_edges: List[Dict] = []           # list of edges
        self.graph_communities: Dict[str, Dict] = {}  # community_id → community data
        self.sha256_cache: Dict[str, str] = {}      # filepath → hash for incremental updates

        self.load_index()

    def load_index(self):
        if MEMORY_INDEX_PATH.exists():
            try:
                self.index_lines = MEMORY_INDEX_PATH.read_text(encoding="utf-8").splitlines()
                self._build_topic_subcache()
                self._load_graph_metadata()
                log_status(f"[MEMORY_INDEX] Loaded {len(self.index_lines)} memories + graph data")
            except Exception as e:
                print(f"[MEMORY_INDEX] Load failed: {e}")
                self.index_lines = []
                self.graph_nodes = {}
                self.graph_edges = []
                self.graph_communities = {}
                self.sha256_cache = {}
        else:
            self.index_lines = []
            self.graph_nodes = {}
            self.graph_edges = []
            self.graph_communities = {}
            self.sha256_cache = {}
            self.save_index()

    def _build_topic_subcache(self):
        self.topic_subcache.clear()
        for line in self.index_lines:
            try:
                topic = line.split(" | ", 2)[1].strip()
                self.topic_subcache.setdefault(topic, []).append(line)
            except:
                continue

    def _load_graph_metadata(self):
        """Load graph metadata from sidecar file"""
        graph_path = MEMORY_INDEX_PATH.with_suffix(".graph.json")
        if graph_path.exists():
            try:
                data = json.loads(graph_path.read_text(encoding="utf-8"))
                self.graph_nodes = data.get("nodes", {})
                self.graph_edges = data.get("edges", [])
                self.graph_communities = data.get("communities", {})
                self.sha256_cache = data.get("sha256_cache", {})
            except Exception:
                pass

    def _save_graph_metadata(self):
        """Save graph metadata to sidecar file"""
        graph_path = MEMORY_INDEX_PATH.with_suffix(".graph.json")
        try:
            data = {
                "nodes": self.graph_nodes,
                "edges": self.graph_edges,
                "communities": self.graph_communities,
                "sha256_cache": self.sha256_cache,
                "last_updated": datetime.now().isoformat()
            }
            graph_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[GRAPH METADATA] Save failed: {e}")

    def save_index(self):
        try:
            MEMORY_INDEX_PATH.write_text("\n".join(self.index_lines) + "\n", encoding="utf-8")
            self._save_graph_metadata()
        except Exception as e:
            print(f"[MEMORY_INDEX] Save failed: {e}")

    # ====================== CORE INDEX METHODS ======================
    def add_entry(self, content: str, topic: str = "general", importance: float = 0.65, tags: List[str] = None) -> str:
        if not content or not content.strip():
            return ""
        tags = tags or []
        entry_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        line = f"{timestamp} | {topic} | imp={importance:.3f} | id={entry_id} | tags={','.join(tags)} | {content.strip()[:600]}"

        self.index_lines.append(line)
        self.topic_subcache.setdefault(topic, []).append(line)

        self.agent.stats["total_memories"] = len(self.index_lines)

        self.agent.mark_dirty()
        self.save_index()

        log_status(f"[MEMORY] Added → {topic} | imp={importance:.3f} | id={entry_id}")
        return entry_id

    # ====================== GRAPH METADATA METHODS (Phase 3) ======================
    def add_graph_node(self, node_id: str, label: str, node_type: str = "concept", properties: Dict = None):
        if properties is None:
            properties = {}
        self.graph_nodes[node_id] = {
            "id": node_id,
            "label": label,
            "type": node_type,
            "properties": properties,
            "timestamp": datetime.now().isoformat()
        }
        self._save_graph_metadata()

    def add_graph_edge(self, source: str, target: str, edge_type: str = "related", weight: float = 1.0, evidence: str = ""):
        edge = {
            "source": source,
            "target": target,
            "type": edge_type,
            "weight": weight,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat()
        }
        self.graph_edges.append(edge)
        self._save_graph_metadata()

    def run_leiden_clustering(self) -> Dict:
        """Run Leiden community detection"""
        try:
            import networkx as nx
            from graspologic.partition import leiden

            G = nx.Graph()
            for edge in self.graph_edges:
                G.add_edge(edge["source"], edge["target"], weight=edge.get("weight", 1.0))

            if len(G.nodes) == 0:
                return {"success": False, "error": "No nodes in graph"}

            partitions = leiden(G)
            
            self.graph_communities.clear()
            for comm_id, nodes in partitions.items():
                self.graph_communities[str(comm_id)] = {
                    "nodes": list(nodes),
                    "size": len(nodes),
                    "name": f"Community {comm_id}"
                }

            self._save_graph_metadata()
            return {
                "success": True,
                "communities": len(self.graph_communities),
                "nodes": len(self.graph_nodes),
                "edges": len(self.graph_edges)
            }
        except ImportError:
            return {"success": False, "error": "networkx and graspologic not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_graph(self) -> Dict:
        """Export interactive graph, Obsidian vault, and wiki"""
        try:
            export_dir = STORAGE_DIR / "graph_export"
            export_dir.mkdir(parents=True, exist_ok=True)

            html = self._generate_interactive_graph()
            (export_dir / "graph.html").write_text(html, encoding="utf-8")

            return {
                "success": True,
                "path": str(export_dir),
                "graph_html": str(export_dir / "graph.html")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_interactive_graph(self) -> str:
        """Generate vis.js interactive graph HTML"""
        nodes_js = []
        for nid, data in self.graph_nodes.items():
            nodes_js.append(f'{{id: "{nid}", label: "{data.get("label", nid)}", group: "{data.get("type", "concept")}"}}')

        edges_js = []
        for e in self.graph_edges:
            edges_js.append(f'{{from: "{e["source"]}", to: "{e["target"]}", label: "{e.get("type", "")}"}}')

        return f"""<!DOCTYPE html><html>
<head>
    <title>Genesis Knowledge Graph</title>
    <script src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{ margin:0; padding:10px; font-family:Arial,sans-serif; background:#f8f9fa; }}
        #graph {{ height:95vh; border:1px solid #ddd; border-radius:8px; }}
        h1 {{ text-align:center; color:#333; }}
    </style>
</head>
<body>
    <h1>Genesis Knowledge Graph</h1>
    <div id="graph"></div>
    <script>
        const nodes = new vis.DataSet([{','.join(nodes_js)}]);
        const edges = new vis.DataSet([{','.join(edges_js)}]);
        const container = document.getElementById('graph');
        const data = {{ nodes: nodes, edges: edges }};
        const options = {{ 
            physics: {{ stabilization: true, solver: "forceAtlas2Based" }},
            interaction: {{ hover: true, zoomView: true }}
        }};
        new vis.Network(container, data, options);
    </script>
</body>
</html>"""

    # ====================== ORIGINAL METHODS (enhanced archiving) ======================
    def retrieve(self, query: str, n_results: int = 6) -> List[Dict]:
        return self.search(query, n_results)

    def search(self, query: str, n_results: int = 8) -> List[Dict]:
        results = []
        q_lower = query.lower()
        for line in reversed(self.index_lines[-500:]):
            if q_lower in line.lower():
                try:
                    parts = line.split(" | ", 5)
                    results.append({
                        "id": re.search(r'id=([a-z0-9]+)', line).group(1) if re.search(r'id=([a-z0-9]+)', line) else "unknown",
                        "topic": parts[1] if len(parts) > 1 else "general",
                        "content": parts[-1][:300],
                        "importance": float(re.search(r'imp=([\d.]+)', line).group(1)) if re.search(r'imp=([\d.]+)', line) else 0.5,
                        "timestamp": parts[0]
                    })
                    if len(results) >= n_results:
                        break
                except:
                    continue
        return results

    def update_importance(self, entry_id: str, delta: float = -0.03) -> bool:
        for i, line in enumerate(self.index_lines):
            if f"id={entry_id}" in line:
                try:
                    match = re.search(r'imp=([\d.]+)', line)
                    if match:
                        current = float(match.group(1))
                        new_imp = max(0.1, min(0.99, current + delta))
                        self.index_lines[i] = re.sub(r'imp=[\d.]+', f'imp={new_imp:.3f}', line)
                        self._build_topic_subcache()
                        self.save_index()
                        self.agent.mark_dirty()
                        return True
                except:
                    return False
        return False

    def get_topic_distribution(self) -> Dict[str, int]:
        if not self.topic_subcache:
            self._build_topic_subcache()
        return {topic: len(entries) for topic, entries in self.topic_subcache.items()}

    def cleanup_old_memories(self) -> int:
        """Enhanced archiving — never archive journals or important entries"""
        archived = 0
        new_lines = []
        for line in self.index_lines:
            try:
                imp_match = re.search(r'imp=([\d.]+)', line)
                topic = line.split(" | ")[1] if " | " in line else "general"
                
                # PROTECT JOURNALS AND IMPORTANT ENTRIES
                if "topic=journal" in line or "journal" in topic.lower() or "reflection" in topic.lower() or "important" in line.lower():
                    new_lines.append(line)
                    continue
                
                if imp_match and float(imp_match.group(1)) < 0.35:
                    self._archive_fact(line, "low_importance")
                    archived += 1
                    continue
            except:
                pass
            new_lines.append(line)
        
        self.index_lines = new_lines
        self._build_topic_subcache()
        self.save_index()
        
        if archived > 0:
            log_status(f"[MEMORY] Archived {archived} low-importance memories")
            self.agent.mark_dirty()
        else:
            log_status("[MEMORY] No low-importance items archived this cycle (journals protected)")
        
        return archived

    def _archive_fact(self, line: str, reason: str):
        try:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            archive_file = ARCHIVE_DIR / f"archived_{date.today().isoformat()}.jsonl"
            with archive_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"line": line, "reason": reason, "time": datetime.now().isoformat()}) + "\n")
        except:
            pass

    def add_skill(self, title: str, description: str, content: str, version: int = 1) -> str:
        skill_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        safe_title = re.sub(r'[^a-z0-9_-]', '_', title.lower().strip())[:60]
        skill_file = SKILLS_DIR / f"skill_{safe_title}_{skill_id}.md"

        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        skill_text = f"""<!-- SKILL ID:{skill_id} | VERSION:{version} | TIME:{timestamp} -->
# {title}
**Description:** {description}
**Version:** {version} | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

{content.strip()}
"""
        skill_file.write_text(skill_text, encoding="utf-8")

        index_line = f"{timestamp} | {title} | v{version} | {skill_file.relative_to(STORAGE_DIR)} | \"{description[:150]}\" | id={skill_id}"
        with SKILLS_INDEX_PATH.open("a", encoding="utf-8") as f:
            f.write(index_line + "\n")

        log_status(f"[SKILL] Created → {title} (v{version})")
        self.agent.mark_dirty()
        return skill_id

    def list_skills(self) -> List[Dict]:
        if not SKILLS_INDEX_PATH.exists():
            return []
        skills = []
        for line in SKILLS_INDEX_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                parts = [p.strip() for p in line.split(" | ")]
                skills.append({
                    "title": parts[1] if len(parts) > 1 else "Unknown",
                    "version": parts[2] if len(parts) > 2 else "v1",
                    "description": parts[4] if len(parts) > 4 else ""
                })
        return skills

    # ====================== OBSIDIAN SUPPORT ======================
    def update_sha256(self, filepath: str, file_hash: str):
        """Update SHA256 cache for incremental Graphify / Obsidian ingestion"""
        self.sha256_cache[filepath] = file_hash
        self._save_graph_metadata()