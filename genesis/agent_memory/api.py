"""
Genesis v5.6.9 Cerberus OmniPalace — API Module
FastAPI server for memory, retrieval, and agent control.
Updated with full Obsidian Wiki endpoints.
"""

from __future__ import annotations

import sys

from ..dependencies import HAS_FASTAPI
from .core import AgentMemory


# ====================== FASTAPI SERVER ======================
def create_api_app(state: AgentMemory):
    """Create and configure the FastAPI application for Genesis with Obsidian Wiki support"""
    if not HAS_FASTAPI:
        print("[API] FastAPI not installed — API server unavailable.")
        print("Install with: pip install fastapi uvicorn")
        return None

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    app = FastAPI(
        title="Genesis v5.6.9 Cerberus OmniPalace API",
        version="5.6.9",
        description="REST API for memory, retrieval, agent control, and Obsidian Wiki"
    )

    # CORS for easy frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ====================== REQUEST MODELS ======================
    class RetrieveRequest(BaseModel):
        query: str
        n_results: int = 6

    class AddMemoryRequest(BaseModel):
        content: str
        topic: str = "general"
        importance: float = 0.6
        tags: list[str] = []

    class GenerateRequest(BaseModel):
        prompt: str

    class FeedbackRequest(BaseModel):
        cmd: str  # "good", "wrong", "important"
        entry_id: str | None = None

    class WikiRequest(BaseModel):
        action: str = "status"  # compile, heal, status
        path: str | None = None
        depth: str = "light"

    # ====================== ROUTES ======================
    @app.get("/")
    async def root():
        wiki_count = len(list(state.memory.wiki_dir.rglob("*.md"))) if hasattr(state.memory, 'wiki_dir') else 0
        return {
            "status": "running",
            "version": "5.6.9",
            "name": "Genesis Cerberus OmniPalace",
            "message": "Memory agent is online",
            "obsidian_wiki_pages": wiki_count
        }

    @app.post("/retrieve")
    async def api_retrieve(req: RetrieveRequest):
        results = state.retrieve(req.query, req.n_results)
        return {
            "success": True,
            "query": req.query,
            "results": results,
            "count": len(results)
        }

    @app.post("/add_memory")
    async def api_add_memory(req: AddMemoryRequest):
        entry_id = state.add(req.content, req.topic, req.importance, req.tags)
        return {
            "success": True,
            "entry_id": entry_id,
            "topic": req.topic,
            "importance": req.importance
        }

    @app.post("/generate")
    async def api_generate(req: GenerateRequest):
        response = state.generate(req.prompt)
        return {
            "success": True,
            "prompt": req.prompt,
            "response": response
        }

    @app.post("/feedback")
    async def api_feedback(req: FeedbackRequest):
        result = state.apply_feedback(req.cmd, req.entry_id)
        return {
            "success": True,
            "message": result
        }

    @app.get("/stats")
    async def api_stats():
        return state.xp.get_stats()

    @app.get("/visualize")
    async def api_visualize():
        return {"visualization": state.visualize_palace_map()}

    @app.post("/new_session")
    async def api_new_session():
        state.reset_session(hard_reset=False)
        return {"success": True, "current_session": state.state.current_session}

    # ====================== NEW OBSIDIAN WIKI API ENDPOINTS ======================
    @app.post("/wiki")
    async def api_wiki(req: WikiRequest):
        if req.action == "compile":
            result = state.compile_obsidian_vault(req.path)
            return {"success": True, "action": "compile", "result": result}
        elif req.action == "heal":
            result = state.heal_wiki(req.depth)
            return {"success": True, "action": "heal", "result": result}
        else:
            wiki_count = len(list(state.memory.wiki_dir.rglob("*.md"))) if hasattr(state.memory, 'wiki_dir') else 0
            return {
                "success": True,
                "action": "status",
                "wiki_pages": wiki_count,
                "vault_path": str(state.memory.vault_dir)
            }

    @app.get("/tools")
    async def api_tools():
        return {
            "tools": state.tool_registry.list_tools() if hasattr(state, 'tool_registry') else []
        }

    @app.get("/user")
    async def api_user():
        return {
            "user_name": state.state.user_name,
            "level": state.state.level,
            "total_xp": state.state.total_xp
        }

    return app


def run_api_server(state: AgentMemory, port: int = None):
    """Convenience function to run the API server"""
    if not HAS_FASTAPI:
        return

    import uvicorn
    app = create_api_app(state)
    
    if app:
        port = port or 8000
        print(f"[API] Starting Genesis API server on http://localhost:{port}")
        print("   Obsidian Wiki endpoints available at /wiki")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")