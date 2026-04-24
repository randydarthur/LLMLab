"""
FastAPI server for the LLMLab LLM Router.

Responsibilities:
- Expose OpenAI-compatible /v1/chat/completions
- Mount system + registry + health endpoints
- Initialize ModelRegistry, SessionManager, RoutingEngine
- Initialize BackendFactory + BackendHealthGate + RouterLogger
- Serve as ASGI entrypoint for Hypercorn or any ASGI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

from ..core.read_configs import ConfigLoader
from ..core.model_registry import ModelRegistry
from ..core.session_manager import SessionManager
from ..core.routing_engine import RoutingEngine
from ..core.backend_factory import BackendFactory
from ..core.backend_health import BackendHealthGate
from ..core.router_logger import RouterLogger

from .routes import router as api_router
from .routes import get_engine, get_registry
from .system import create_system_router


# ------------------------------------------------------------
# Application Factory
# ------------------------------------------------------------

def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI app.
    Exported.
    """
    app = FastAPI(title="LLMLab LLM Router", version="1.0.0")

    # ------------------------------------------------------------
    # CORS (useful for local tools + cross-platform clients)
    # ------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------
    # Load YAML configs + initialize core components
    # ------------------------------------------------------------
    config = ConfigLoader.load_router_config("router/configs")

    registry = ModelRegistry(config)
    registry.initialize()  # Discover backends + models

    session_manager = SessionManager(config)
    routing_engine = RoutingEngine(config, registry, session_manager)

    backend_factory = BackendFactory(config)
    health_gate = BackendHealthGate(ttl_seconds=10)
    logger = RouterLogger(json_mode=False)

    start_time = time.time()

    # ------------------------------------------------------------
    # Dependency injection for routes.py
    # ------------------------------------------------------------
    app.dependency_overrides = {
        "get_engine": lambda: routing_engine,
        "get_registry": lambda: registry,
    }

    # ------------------------------------------------------------
    # Mount API routes
    # ------------------------------------------------------------
    app.dependency_overrides[get_engine] = lambda: routing_engine
    app.dependency_overrides[get_registry] = lambda: registry

    app.include_router(api_router)


    # ------------------------------------------------------------
    # Mount system observability routes
    # ------------------------------------------------------------
    system_router = create_system_router(
        logger=logger,
        health_gate=health_gate,
        registry=registry,
        backend_factory=backend_factory,
        start_time=start_time,
    )
    app.include_router(system_router)

    return app


# ------------------------------------------------------------
# ASGI Entrypoint
# ------------------------------------------------------------

# Hypercorn (or any ASGI server) imports this:
app = create_app()

