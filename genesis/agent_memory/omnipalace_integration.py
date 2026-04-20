"""
Genesis v5.6.9 Cerberus OmniPalace — OmniPalaceManager
Full spatial memory palace system with rooms, portals, atomic memories,
tight integration with Obsidian Wiki, Hall of Records auto-routing,
and enhanced 3D visualization export.
"""

from __future__ import annotations
import random
import time
import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from ..config import log_status, STORAGE_DIR, CONFIG
from .core import AgentMemory


class OmniPalaceManager:
    """OmniPalace — Spatial memory palace with Obsidian Wiki integration, Hall of Records, and 3D export."""

    def __init__(self, agent: AgentMemory):
        self.agent = agent
        self.rooms: Dict[str, Dict] = {}
        self.portals: Dict[str, List[str]] = {}
        self.atomic_memories: List[Dict] = []
        self.current_room = "Entrance Hall"
        self.active_sub_agents: List[str] = []
        self._init_default_rooms()

    def _init_default_rooms(self):
        """Initialize rich default rooms with Hall of Records and 3D coordinates."""
        self.rooms = {
            "Entrance Hall": {
                "theme": "🌟 Welcome & Overview",
                "description": "Main entry point and central hub. Connects to all wings.",
                "color": "gold",
                "coherence": 0.95,
                "x": 0, "y": 0, "z": 0
            },
            "Memory Library": {
                "theme": "📚 Long-term Knowledge",
                "description": "Core facts, memories, and general knowledge",
                "color": "blue",
                "coherence": 0.90,
                "x": 8, "y": 3, "z": 1
            },
            "Reflection Grove": {
                "theme": "🌲 Introspection & Growth",
                "description": "Reflections, insights, and personal development",
                "color": "green",
                "coherence": 0.85,
                "x": -8, "y": 4, "z": 3
            },
            "Prediction Tower": {
                "theme": "🔮 Future Planning",
                "description": "Forward predictions and scenario planning",
                "color": "purple",
                "coherence": 0.80,
                "x": 2, "y": 12, "z": 8
            },
            "Skill Forge": {
                "theme": "🔨 Tools & Abilities",
                "description": "Created skills, tools, and workflows",
                "color": "orange",
                "coherence": 0.88,
                "x": 10, "y": -5, "z": -3
            },
            "Journal Archive": {
                "theme": "📖 Personal History",
                "description": "Journals and episodic memories",
                "color": "brown",
                "coherence": 0.92,
                "x": -10, "y": -6, "z": 2
            },
            "Cerberus Chamber": {
                "theme": "⚖️ Multi-Agent Reasoning",
                "description": "Debate harness and complex analysis",
                "color": "red",
                "coherence": 0.75,
                "x": 5, "y": 7, "z": -6
            },
            "Wiki Atrium": {
                "theme": "📖 Obsidian Knowledge Vault",
                "description": "Living Obsidian wiki — compiled, linked, and self-healing",
                "color": "cyan",
                "coherence": 0.93,
                "x": -5, "y": 9, "z": 5
            },
            "Hall of Records": {
                "theme": "🏛️ Session Logs & History",
                "description": "Permanent archive of all sessions, journals, transcripts, and chronological events. Spatial links show relationships across time.",
                "color": "silver",
                "coherence": 0.96,
                "x": 0, "y": 0, "z": 12
            },
            "World Observatory": {
                "theme": "🌍 External Knowledge & Tools",
                "description": "All world knowledge learned via web search, news, tools, and real-time events. Dynamically expands.",
                "color": "teal",
                "coherence": 0.91,
                "x": 15, "y": 8, "z": 4
            },
            "Registry Wing": {
                "theme": "🪪 User Profiles & Social Graph",
                "description": "Persistent user profiles, trust levels, relationships, and social metrics",
                "color": "violet",
                "coherence": 0.88,
                "x": -12, "y": 2, "z": 6
            }
        }

    def compute_novelty(self, content: str) -> float:
        """Compute novelty score for memory ingestion."""
        if not content or len(content) < 10:
            return 0.3
        length_score = min(1.0, len(content) / 300)
        fresh_keywords = ["today", "now", "current", "latest", "new", "update", "weather", "news", "happened", "session", "journal", "yesterday", "april", "transcript", "history", "previous"]
        keyword_score = 0.4 if any(k in content.lower() for k in fresh_keywords) else 0.0
        variance = random.uniform(0.05, 0.25)
        return min(0.95, length_score + keyword_score + variance)

    def add_atomic(self, content: str, tags: List[str] = None):
        """Add atomic memory to current room with intelligent routing."""
        tags = tags or ["atomic"]
        novelty = self.compute_novelty(content)
        
        room = self._route_to_palace_room(content, tags)
        
        entry = {
            "content": content,
            "tags": tags,
            "timestamp": datetime.now().isoformat(),
            "room": room,
            "novelty": novelty,
            "id": f"mem_{int(time.time()*1000)}"
        }
        self.atomic_memories.append(entry)
        
        if hasattr(self.agent, 'add'):
            self.agent.add(content, topic="atomic", importance=0.9, tags=tags + [f"room:{room}"])
        
        log_status(f"[PALACE] Added atomic memory to {room} (novelty: {novelty:.2f})")

    def _route_to_palace_room(self, content: str, tags: List[str]) -> str:
        """Cerberus-driven intelligent routing — Hall of Records priority for sessions/journals/history."""
        lower_content = content.lower()
        lower_tags = [t.lower() for t in tags]

        if any(k in lower_content or k in lower_tags for k in ["session", "journal", "yesterday", "april", "history", "log", "transcript", "previous", "earlier", "what happened", "last session"]):
            return "Hall of Records"
        
        if "wiki" in lower_content or "obsidian" in lower_content:
            return "Wiki Atrium"
        if any(k in lower_content for k in ["reflect", "coherence", "improve", "audit", "reflection"]):
            return "Reflection Grove"
        if any(k in lower_content for k in ["predict", "future", "plan", "prediction"]):
            return "Prediction Tower"
        if any(k in lower_content for k in ["skill", "tool", "create", "upgrade"]):
            return "Skill Forge"
        if any(k in lower_content for k in ["web", "search", "news", "world", "tool", "external"]):
            return "World Observatory"

        try:
            routing = self.agent.cerberus.run_with_context(
                f"Route this memory to ONE existing OmniPalace room. Available rooms: {list(self.rooms.keys())}. Return ONLY the room name.\n\n{content[:500]}"
            )
            for room in self.rooms:
                if room.lower() in routing.lower():
                    return room
        except:
            pass

        return "Memory Library"

    def visualize_palace_map(self) -> str:
        """Full palace visualization with Hall of Records emphasis."""
        out = ["\n🌟 === OMNIPALACE MAP ==="]
        out.append(f"📍 Current Location: {self.current_room}\n")
        
        for room, data in self.rooms.items():
            marker = "→ " if room == self.current_room else "  "
            theme = data.get("theme", room)
            coherence = data.get("coherence", 0.8)
            out.append(f"{marker}{room:<22} {theme} (coherence: {coherence:.2f})")
        
        wiki_count = self.agent.get_wiki_status().get("wiki_pages", 0) if hasattr(self.agent, 'get_wiki_status') else 0
        hall_count = sum(1 for m in self.atomic_memories if m.get('room') == 'Hall of Records')
        
        out.append(f"\n🔹 Atomic Memories: {len(self.atomic_memories)}")
        out.append(f"🔹 Hall of Records Entries: {hall_count}")
        out.append(f"🔹 Obsidian Wiki Pages: {wiki_count}")
        out.append(f"🔹 Active Sub-Agents: {len(self.active_sub_agents)}")
        out.append(f"🔹 Portals: {len(self.portals)}")
        out.append("=" * 60)
        return "\n".join(out)

    def create_portal(self, room1: str, room2: str) -> str:
        """Create a portal between two rooms."""
        if room1 not in self.portals:
            self.portals[room1] = []
        if room2 not in self.portals[room1]:
            self.portals[room1].append(room2)
        return f"Portal created between {room1} and {room2}."

    def enter_palace_room(self, room_name: str) -> str:
        """Enter or create a room."""
        if room_name in self.rooms:
            self.current_room = room_name
            return f"✅ Entered {room_name}: {self.rooms[room_name]['description']}"
        
        self.rooms[room_name] = {
            "theme": f"🌐 {room_name}",
            "description": f"Custom room: {room_name}",
            "color": "white",
            "coherence": 0.7,
            "x": random.randint(-12, 12),
            "y": random.randint(-12, 12),
            "z": random.randint(-8, 12)
        }
        self.current_room = room_name
        return f"✅ Created and entered new room: {room_name}"

    def pull_memory_to_room(self, memory_id: str, target_room: str) -> str:
        """Pull a specific memory into a room."""
        for mem in self.atomic_memories:
            if mem.get("id") == memory_id or memory_id in mem.get("content", ""):
                mem["room"] = target_room
                return f"Memory moved to {target_room}"
        return "Memory not found."

    def add_to_room(self, room_name: str, content: str, tags: List[str] = None):
        """Add memory to a specific OmniPalace room for method of loci recall."""
        tags = tags or []
        
        if room_name not in self.rooms:
            # Auto-create room if it doesn't exist yet
            self.rooms[room_name] = {
                "theme": f"🌐 {room_name}",
                "description": f"Auto-generated room for {room_name}",
                "color": "white",
                "coherence": 0.8,
                "x": random.randint(-15, 15),
                "y": random.randint(-15, 15),
                "z": random.randint(-8, 12)
            }
        
        entry = {
            "content": content[:800],
            "timestamp": datetime.now().isoformat(),
            "tags": tags,
            "id": f"room_{len(self.rooms[room_name])}"
        }
        
        if "entries" not in self.rooms[room_name]:
            self.rooms[room_name]["entries"] = []
        
        self.rooms[room_name]["entries"].append(entry)
        
        # Also add to main memory system
        if hasattr(self.agent, 'add'):
            self.agent.add(content, topic=room_name.lower().replace(" ", "_"), importance=0.7, tags=tags)
        
        log_status(f"[OMNIPALACE] Added to room '{room_name}' ({len(content)} chars)")
        return True

    def merge_rooms(self, room1: str, room2: str) -> str:
        """Merge two rooms (future roadmap feature)."""
        if room1 in self.rooms and room2 in self.rooms:
            self.rooms[room1]["description"] += f" | Merged with {room2}"
            return f"Rooms {room1} and {room2} merged."
        return "One or both rooms not found."

    def export_3d_palace(self) -> str:
        """Export palace as JSON for 3D visualization tools."""
        nodes = []
        for name, data in self.rooms.items():
            memory_count = len([m for m in self.atomic_memories if m.get("room") == name])
            nodes.append({
                "name": name,
                "theme": data.get("theme"),
                "x": data.get("x", 0),
                "y": data.get("y", 0),
                "z": data.get("z", 0),
                "color": data.get("color", "gray"),
                "coherence": data.get("coherence", 0.8),
                "size": 12 + memory_count * 4,
                "memory_count": memory_count
            })

        edges = []
        for room1, targets in self.portals.items():
            for room2 in targets:
                edges.append({"from": room1, "to": room2})

        palace_3d = {
            "version": "5.6.9",
            "timestamp": datetime.now().isoformat(),
            "current_room": self.current_room,
            "nodes": nodes,
            "edges": edges,
            "total_atomic_memories": len(self.atomic_memories),
            "hall_of_records_count": sum(1 for m in self.atomic_memories if m.get('room') == 'Hall of Records')
        }

        path = STORAGE_DIR / "omnipalace_3d.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(palace_3d, f, indent=2)

        log_status(f"[3D PALACE] Exported to {path}")
        return f"✅ 3D Palace exported to {path}"

    # === RESTORED ORIGINAL VISION: Dynamic growth daemon ===
    def grow_dynamically(self):
        """Auto-create rooms from graph clusters or high-novelty topics."""
        if not hasattr(self.agent.index, 'run_leiden_clustering'):
            return
        try:
            result = self.agent.index.run_leiden_clustering()
            if result.get("success"):
                for comm_id, data in getattr(self.agent.index, 'graph_communities', {}).items():
                    room_name = f"Cluster_{comm_id}"
                    if room_name not in self.rooms:
                        self.rooms[room_name] = {
                            "theme": f"Discovered Cluster {comm_id}",
                            "description": f"Auto-generated from {data.get('size', 0)} related memories",
                            "color": random.choice(["violet","indigo","emerald","amber"]),
                            "coherence": 0.85,
                            "x": random.randint(-20,20), 
                            "y": random.randint(-20,20), 
                            "z": random.randint(0,15)
                        }
                        log_status(f"[OMNIPALACE] Dynamically grew new room: {room_name}")
        except Exception as e:
            log_status(f"[OMNIPALACE] Dynamic growth skipped: {e}")

    def __str__(self):
        wiki_count = self.agent.get_wiki_status().get("wiki_pages", 0) if hasattr(self.agent, 'get_wiki_status') else 0
        hall_count = sum(1 for m in self.atomic_memories if m.get('room') == 'Hall of Records')
        return f"OmniPalace — {len(self.rooms)} rooms | {len(self.atomic_memories)} atomic memories | Hall of Records: {hall_count} | Wiki pages: {wiki_count} | Current: {self.current_room}"