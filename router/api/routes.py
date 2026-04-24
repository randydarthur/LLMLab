"""
API route definitions for the LLMLab LLM Router.

This module contains the actual HTTP route handlers used by the FastAPI server.
It is intentionally separate from server.py to keep the application factory clean.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
import uuid

from ..core.routing_engine import RoutingEngine
from ..core.model_registry import ModelRegistry

router = APIRouter()


# ------------------------------------------------------------
# Dependency Injection
# ------------------------------------------------------------

def get_engine() -> RoutingEngine:
    """
    Placeholder dependency provider.
    The real provider is injected by server.py via app.dependency_overrides.
    Internal only.
    """
    raise RuntimeError("RoutingEngine dependency not configured")


def get_registry() -> ModelRegistry:
    """
    Placeholder dependency provider.
    The real provider is injected by server.py via app.dependency_overrides.
    Internal only.
    """
    raise RuntimeError("ModelRegistry dependency not configured")


# ------------------------------------------------------------
# OpenAI-Compatible Chat Completions
# ------------------------------------------------------------

@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    engine: RoutingEngine = Depends(get_engine),
):
    """
    OpenAI-compatible chat completions endpoint.
    Exported.
    """
    payload = await request.json()

    # Inject session_id if missing
    session_id = payload.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        payload["session_id"] = session_id

    stream = payload.get("stream", False)

    if stream:
        async def stream_generator():
            async for chunk in engine.handle_chat(payload, stream=True):
                # OpenAI-compatible SSE format
                yield f"data: {chunk}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    else:
        result = await engine.handle_chat(payload, stream=False)
        return JSONResponse(result)


# ------------------------------------------------------------
# OpenAI-Compatible Model Listing
# ------------------------------------------------------------

@router.get("/v1/models")
async def list_models_openai(registry: ModelRegistry = Depends(get_registry)):
    """
    OpenAI-compatible model listing.

    Returns:
      {
        "object": "list",
        "data": [
          {
            "id": "qwen2.5:7b",
            "object": "model",
            "owned_by": "local",
            "metadata": {...}
          }
        ]
      }
    """
    return registry.list_models_openai()


# ------------------------------------------------------------
# Internal Registry Endpoints (for REPL + debugging)
# ------------------------------------------------------------

@router.get("/v1/registry/models")
async def list_registry_models(registry: ModelRegistry = Depends(get_registry)):
    """
    Internal rich model list for REPL and debugging.
    """
    return registry.list_models()


@router.get("/v1/registry/backends")
async def list_registry_backends(registry: ModelRegistry = Depends(get_registry)):
    """
    Internal backend list for REPL and debugging.
    """
    return registry.list_backends()


# ------------------------------------------------------------
# Health
# ------------------------------------------------------------

@router.get("/health")
async def health():
    """
    Simple health check endpoint.
    Exported.
    """
    return {"status": "ok"}

