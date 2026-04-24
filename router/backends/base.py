"""
Base class for all backend adapters in the LLMLab LLM Router.

Responsibilities:
- Define a unified interface for chat completions
- Provide availability checks
- Provide model discovery hooks
- Serve as the parent class for Ollama, LM Studio, cloud backends, etc.
"""

from typing import Dict, Any, List, AsyncGenerator
from abc import ABC, abstractmethod


class BackendAdapter(ABC):
    """
    Abstract base class for all backend adapters.
    Exported.
    """

    def __init__(self, name: str, backend_type: str, base_url: str):
        self.name = name
        self.backend_type = backend_type
        self.base_url = base_url

    # ------------------------------------------------------------
    # Required API
    # ------------------------------------------------------------

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
    ) -> Any:
        """
        Perform a chat completion request.
        Must support both streaming and non-streaming modes.
        Exported.
        """
        raise NotImplementedError

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Return True if the backend is reachable and healthy.
        Exported.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Return a list of models available on this backend.
        Exported.
        """
        raise NotImplementedError

    # ------------------------------------------------------------
    # Optional Helpers
    # ------------------------------------------------------------

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """
        Convenience wrapper for streaming chat responses.
        Exported.
        """
        async for chunk in self.chat(model, messages, stream=True):
            yield chunk

    def info(self) -> Dict[str, Any]:
        """
        Return backend metadata for registry inspection.
        Exported.
        """
        return {
            "name": self.name,
            "type": self.backend_type,
            "base_url": self.base_url,
        }

