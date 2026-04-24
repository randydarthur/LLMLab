"""
Unified Model Registry for the LLMLab Router.

Responsibilities:
- Discover all backends (Ollama, LM Studio, cloud, etc.)
- Normalize model metadata into a common internal structure
- Provide lookup utilities for routing decisions
- Provide OpenAI-compatible model listing for agent frameworks
"""

from typing import Dict, List, Optional, Any

from ..backends.ollama_adapter import discover_backends as discover_ollama_backends


class ModelRegistry:
    """
    Central registry of all known models across all backends.
    Exported.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config

        # Internal canonical model map:
        #   { model_name: { name, backend, backend_type, base_url, context, family, quantization, capabilities, raw } }
        self._models: Dict[str, Dict[str, Any]] = []

        # List of backend descriptors
        self._backends: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def initialize(self) -> None:
        """
        Discover all backends and build the model registry.
        Exported.
        """
        self._models = {}
        self._backends = []

        # Ollama (local + LAN)
        for backend in discover_ollama_backends(self._config):
            self._register_backend(backend)

        # Future:
        # - LM Studio
        # - vLLM
        # - Cloud providers
        # - Custom adapters

    def get_model(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Return metadata for a given model name, or None if not found.
        Exported.
        """
        return self._models.get(name)

    def list_models(self) -> List[Dict[str, Any]]:
        """
        Return a list of all registered models (internal rich format).
        Exported.
        """
        return list(self._models.values())

    def list_backends(self) -> List[Dict[str, Any]]:
        """
        Return a list of discovered backends.
        Exported.
        """
        return list(self._backends)

    # ------------------------------------------------------------
    # OpenAI-compatible model listing
    # ------------------------------------------------------------

    def list_models_openai(self) -> Dict[str, Any]:
        """
        Return OpenAI-compatible model list:

        {
          "object": "list",
          "data": [
            {
              "id": "qwen2.5:7b",
              "object": "model",
              "owned_by": "local",
              "metadata": {
                "backend": "ollama",
                "context": 8192,
                "family": "qwen",
                "quantization": "Q4_K_M",
                "capabilities": ["general"],
                "raw": {...}
              }
            }
          ]
        }
        """
        data = []

        for m in self._models.values():
            data.append(
                {
                    "id": m["name"],
                    "object": "model",
                    "owned_by": "local",
                    "metadata": {
                        "backend": m.get("backend"),
                        "backend_type": m.get("backend_type"),
                        "context": m.get("context"),
                        "family": m.get("family"),
                        "quantization": m.get("quantization"),
                        "capabilities": m.get("capabilities", []),
                        "raw": m.get("raw", {}),
                    },
                }
            )

        return {"object": "list", "data": data}

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    def _register_backend(self, backend_info: Dict[str, Any]) -> None:
        """
        Register a backend and all of its models.
        Internal.
        """
        self._backends.append(backend_info)

        backend_name = backend_info["name"]
        backend_type = backend_info["type"]
        base_url = backend_info["base_url"]
        models = backend_info.get("models", [])

        for model in models:
            model_name = model["name"]

            # Normalize metadata
            capabilities = model.get("capabilities", ["general"])
            context_length = model.get("context_length", 8192)
            family = model.get("family")
            quant = model.get("quantization")

            # Store canonical descriptor
            self._models[model_name] = {
                "name": model_name,
                "backend": backend_name,
                "backend_type": backend_type,
                "base_url": base_url,
                "capabilities": capabilities,
                "context": context_length,
                "family": family,
                "quantization": quant,
                "raw": model,  # backend-specific metadata preserved
            }

