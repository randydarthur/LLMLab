"""
Routing Engine for the LLMLab LLM Router.

Responsibilities:
- Apply routing rules
- Maintain session affinity
- Select best model for a task
- Dispatch requests to backend adapters
- Support streaming and non-streaming responses
- Produce OpenAI-compatible output
"""

from typing import Dict, Any, List, Optional, AsyncGenerator

from .model_registry import ModelRegistry
from .session_manager import SessionManager
from .task_classifier import TaskClassifier
from .backend_factory import BackendFactory
from .backend_health import BackendHealthGate
from ..backends.base import BackendAdapter


class RoutingEngine:
    """
    Central routing engine for the LLMLab router.
    Exported.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        registry: ModelRegistry,
        session_manager: SessionManager,
    ):
        self._config = config
        self._registry = registry
        self._session_manager = session_manager
        self._classifier = TaskClassifier(config)

        self._factory = BackendFactory(config)
        self._health = BackendHealthGate(ttl_seconds=10)

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    async def handle_chat(
        self,
        payload: Dict[str, Any],
        stream: bool = False,
    ) -> Any:
        """
        Main entrypoint for chat completions.
        Exported.
        """
        session_id = payload["session_id"]
        messages = payload["messages"]

        # 1. Load or initialize session metadata
        metadata = await self._session_manager.get_session_metadata(session_id)

        # 2. Determine model (session affinity or routing)
        model_name = await self._select_model(payload, metadata)

        # 3. Update session metadata
        await self._session_manager.set_session_metadata(
            session_id,
            {"model": model_name},
        )

        # 4. Append latest user message
        await self._session_manager.append_message(session_id, messages[-1])

        # 5. Retrieve full history
        history = await self._session_manager.get_history(session_id)

        # 6. Dispatch to backend
        backend = await self._get_backend_for_model(model_name)

        if stream:
            return self._stream_chat(backend, model_name, history)
        else:
            return await self._nonstream_chat(backend, model_name, history)

    # ------------------------------------------------------------
    # Model Selection
    # ------------------------------------------------------------

    async def _select_model(
        self,
        payload: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Determine which model to use.
        Exported (but internal to routing logic).
        """
        # 1. User explicitly requested a model
        if payload.get("model"):
            return payload["model"]

        # 2. Session already pinned to a model
        if "model" in metadata:
            return metadata["model"]

        # 3. Classify task
        task = self._classifier.classify(payload["messages"])

        # 4. Choose best model for task
        return self._choose_model_for_task(task)

    def _choose_model_for_task(self, task: str) -> str:
        """
        Select best model for a given task.
        Internal.
        """
        task_cfg = self._config.get("tasks", {})
        if task in task_cfg:
            preferred = task_cfg[task].get("preferred_models", [])
            for m in preferred:
                if self._registry.get_model(m):
                    return m

        # Fallback to default model
        return self._config.get("default_model", "qwen2.5:7b")

    # ------------------------------------------------------------
    # Backend Dispatch
    # ------------------------------------------------------------

    async def _get_backend_for_model(self, model_name: str) -> BackendAdapter:
        """
        Return a healthy backend adapter instance for a given model.
        """
        model = self._registry.get_model(model_name)
        if not model:
            raise ValueError(f"Unknown model: {model_name}")

        backend_name = model["backend"]

        backend_info = next(
            b for b in self._registry.list_backends()
            if b["name"] == backend_name
        )

        adapter = self._factory.get_adapter(backend_info)

        # Health gating
        return await self._health.get_healthy_adapter(adapter)

    # ------------------------------------------------------------
    # Non-Streaming Chat
    # ------------------------------------------------------------

    async def _nonstream_chat(
        self,
        backend: BackendAdapter,
        model_name: str,
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Non-streaming chat completion.
        Returns OpenAI-compatible dict.
        """
        return await backend.chat(model_name, history, stream=False)

    # ------------------------------------------------------------
    # Streaming Chat
    # ------------------------------------------------------------

    async def _stream_chat(
        self,
        backend: BackendAdapter,
        model_name: str,
        history: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat responses from backend.
        Produces OpenAI-compatible SSE chunks.
        """
        async for token in backend.chat(model_name, history, stream=True):
            # OpenAI-compatible SSE chunk
            yield json.dumps({
                "id": "stream",
                "object": "chat.completion.chunk",
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": token},
                        "finish_reason": None,
                    }
                ],
            })

        # Final termination message
        yield "data: [DONE]"

