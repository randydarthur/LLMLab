"""
Ollama backend adapter for the LLMLab LLM Router.

Implements the BackendAdapter interface using Ollama's HTTP API:
- /api/chat for chat completions (streaming + non-streaming)
- /api/tags for model discovery
- /api/show for detailed model metadata
"""

from typing import Dict, Any, List, AsyncGenerator
import aiohttp
import json
import asyncio

from .base import BackendAdapter


# ------------------------------------------------------------
# Reachability
# ------------------------------------------------------------

async def _is_reachable(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        return True
    except Exception:
        return False


# ------------------------------------------------------------
# Model Metadata Fetching
# ------------------------------------------------------------

async def _fetch_tags(host: str, port: int) -> List[Dict[str, Any]]:
    """
    Returns Ollama's /api/tags payload:
    {
      "models": [
        { "name": "qwen2.5:7b", "modified_at": "...", ... }
      ]
    }
    """
    url = f"http://{host}:{port}/api/tags"
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("models", [])


async def _fetch_model_info(base_url: str, name: str) -> Dict[str, Any]:
    """
    Calls /api/show to get detailed metadata for a model.
    Returns {} on failure.
    """
    url = f"{base_url}/api/show"
    payload = {"model": name}

    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=2) as resp:
                if resp.status != 200:
                    return {}
                return await resp.json()
    except Exception:
        return {}


# ------------------------------------------------------------
# Backend Discovery
# ------------------------------------------------------------

def _build_candidate_hosts(config):
    hosts = ["127.0.0.1"]
    hosts.extend(config.get("lan_hosts", []))
    return hosts


def discover_backends(config):
    """
    Synchronous wrapper for async backend discovery.
    Works whether or not an event loop is already running.
    """
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(
            _discover_backends_async(config), loop
        )
        return future.result()
    except RuntimeError:
        return asyncio.run(_discover_backends_async(config))


async def _discover_backends_async(config):
    hosts = _build_candidate_hosts(config)
    port = config.get("port", 11434)

    backends = []

    for host in hosts:
        if not await _is_reachable(host, port):
            continue

        tags = await _fetch_tags(host, port)
        base_url = f"http://{host}:{port}"

        # Normalize model metadata
        models = []
        for item in tags:
            name = item.get("name")
            if not name:
                continue

            # Fetch detailed metadata
            info = await _fetch_model_info(base_url, name)

            models.append(
                {
                    "name": name,
                    "capabilities": ["general", "chat"],
                    "context_length": info.get("context_length", 8192),
                    "family": info.get("family"),
                    "quantization": info.get("quantization"),
                    "raw": info,
                }
            )

        backends.append(
            {
                "name": f"ollama-{host}",
                "type": "ollama",
                "base_url": base_url,
                "models": models,
            }
        )

    return backends


# ------------------------------------------------------------
# Backend Adapter
# ------------------------------------------------------------

class OllamaBackendAdapter(BackendAdapter):
    """
    Backend adapter for an Ollama server.
    Exported.
    """

    def __init__(self, name: str, base_url: str):
        super().__init__(name=name, backend_type="ollama", base_url=base_url)

    # ------------------------------------------------------------
    # Chat Completion
    # ------------------------------------------------------------

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
    ) -> Any:
        """
        Perform a chat completion request using Ollama's /api/chat endpoint.
        Supports streaming and non-streaming modes.
        Exported.
        """
        url = f"{self.base_url}/api/chat"
        payload = {"model": model, "messages": messages, "stream": stream}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if stream:
                    return self._stream_response(resp)
                else:
                    data = await resp.json()
                    return self._normalize_nonstream(data)

    # ------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------

    async def _stream_response(
        self,
        resp: aiohttp.ClientResponse,
    ) -> AsyncGenerator[str, None]:
        """
        Stream SSE chunks from Ollama.
        Internal.
        """
        async for raw_line in resp.content:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue

            # Ollama streams JSON lines
            try:
                data = json.loads(line)
            except Exception:
                continue

            # Extract token
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                yield chunk

    # ------------------------------------------------------------
    # Non-Streaming Normalization
    # ------------------------------------------------------------

    def _normalize_nonstream(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Ollama's non-streaming response into OpenAI-like format.
        Internal.
        """
        msg = data.get("message", {})
        return {
            "id": data.get("id", "ollama"),
            "object": "chat.completion",
            "model": data.get("model"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": msg.get("role", "assistant"),
                        "content": msg.get("content", ""),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": None,
        }

    # ------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------

    async def is_available(self) -> bool:
        """
        Check if Ollama is reachable by calling /api/tags.
        Exported.
        """
        url = f"{self.base_url}/api/tags"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=2) as resp:
                    return resp.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------
    # Model Discovery
    # ------------------------------------------------------------

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Return a list of normalized model descriptors for this backend.
        Exported.
        """
        url = f"{self.base_url}/api/tags"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as resp:
                    if resp.status != 200:
                        return []
                    payload = await resp.json()
        except Exception:
            return []

        models = []
        for item in payload.get("models", []):
            name = item.get("name")
            if not name:
                continue

            info = await _fetch_model_info(self.base_url, name)

            models.append(
                {
                    "name": name,
                    "capabilities": ["general", "chat"],
                    "context_length": info.get("context_length", 8192),
                    "family": info.get("family"),
                    "quantization": info.get("quantization"),
                    "raw": info,
                }
            )

        return models

