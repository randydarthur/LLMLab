"""
Backend Factory for the LLMLab LLM Router.

Responsibilities:
- Convert ModelRegistry backend entries into concrete backend adapter instances
- Cache adapters for reuse
- Provide a lookup API for RoutingEngine
- Normalize backend metadata for future multi-backend support
"""

from typing import Dict, Any
from ..backends.ollama_adapter import OllamaBackendAdapter
from ..backends.base import BackendAdapter


class BackendFactory:
    """
    Factory that instantiates backend adapters based on registry metadata.
    Exported.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config

        # Cache of instantiated adapters:
        #   { backend_name: adapter_instance }
        self._cache: Dict[str, BackendAdapter] = {}

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def get_adapter(self, backend_info: Dict[str, Any]) -> BackendAdapter:
        """
        Return a backend adapter instance for the given backend_info.
        Exported.

        backend_info is a normalized descriptor from ModelRegistry:
        {
            "name": "ollama-local",
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "models": [...]
        }
        """
        name = backend_info["name"]

        # Cached?
        if name in self._cache:
            return self._cache[name]

        adapter = self._create_adapter(backend_info)
        self._cache[name] = adapter
        return adapter

    # ------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------

    def _create_adapter(self, backend_info: Dict[str, Any]) -> BackendAdapter:
        """
        Instantiate the correct backend adapter based on backend type.
        Internal.
        """
        backend_type = backend_info["type"]
        base_url = backend_info["base_url"]
        name = backend_info["name"]

        # -------------------------------
        # Ollama (local or LAN)
        # -------------------------------
        if backend_type in ("ollama", "local-ollama"):
            return OllamaBackendAdapter(
                name=name,
                base_url=base_url,
            )

        # -------------------------------
        # Future backends
        # -------------------------------
        # if backend_type == "lmstudio":
        #     return LMStudioBackendAdapter(name=name, base_url=base_url)
        #
        # if backend_type == "vllm":
        #     return VLLMBackendAdapter(name=name, base_url=base_url)
        #
        # if backend_type == "openai":
        #     return OpenAIBackendAdapter(name=name, base_url=base_url, api_key=...)

        raise ValueError(f"Unsupported backend type: {backend_type}")

