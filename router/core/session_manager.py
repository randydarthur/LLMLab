"""
Session Manager for the LLMLab LLM Router.

Responsibilities:
- Maintain session affinity (model, backend)
- Store full message history
- Enforce TTL expiration
- Prune history when exceeding context window
- Provide atomic Redis-backed operations
"""

from typing import List, Dict, Any, Optional
import json
import time
import redis.asyncio as redis


class SessionManager:
    """
    Redis-backed session manager.
    Exported.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        redis_cfg = config.get("redis", {})
        self._ttl = redis_cfg.get("ttl_seconds", 3600)

        self._redis = redis.Redis(
            host=redis_cfg.get("host", "localhost"),
            port=redis_cfg.get("port", 6379),
            db=redis_cfg.get("db", 0),
            decode_responses=True,
        )

    # ------------------------------------------------------------
    # Public API — Metadata
    # ------------------------------------------------------------

    async def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """
        Return session metadata (model, backend, timestamps).
        Exported.
        """
        key = f"session:{session_id}"
        data = await self._redis.hgetall(key)
        await self._redis.expire(key, self._ttl)
        return data or {}

    async def set_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> None:
        """
        Set or update session metadata.
        Exported.
        """
        key = f"session:{session_id}"
        await self._redis.hset(key, mapping=metadata)
        await self._redis.expire(key, self._ttl)

    # ------------------------------------------------------------
    # Public API — Message History
    # ------------------------------------------------------------

    async def append_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Append a message to the session history.
        Exported.
        """
        key = f"session:{session_id}:messages"
        await self._redis.rpush(key, json.dumps(message))
        await self._redis.expire(key, self._ttl)

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Return full message history for a session.
        Exported.
        """
        key = f"session:{session_id}:messages"
        raw = await self._redis.lrange(key, 0, -1)
        await self._redis.expire(key, self._ttl)
        return [json.loads(m) for m in raw]

    # ------------------------------------------------------------
    # Context Window Pruning
    # ------------------------------------------------------------

    async def prune_history(self, session_id: str, max_tokens: int) -> None:
        """
        Prune history to fit within a context window.
        Exported.

        NOTE:
        - This is a token-count-based pruning strategy.
        - It removes oldest messages until the estimated token count fits.
        - Token estimation is intentionally simple and backend-agnostic.
        """
        key = f"session:{session_id}:messages"
        raw = await self._redis.lrange(key, 0, -1)
        if not raw:
            return

        # Estimate tokens (very rough heuristic)
        def estimate_tokens(msg: Dict[str, Any]) -> int:
            content = msg.get("content", "")
            return max(1, len(content.split()))

        messages = [json.loads(m) for m in raw]
        total = sum(estimate_tokens(m) for m in messages)

        # If already within limit, nothing to prune
        if total <= max_tokens:
            return

        # Remove oldest messages until within limit
        while messages and total > max_tokens:
            removed = messages.pop(0)
            total -= estimate_tokens(removed)

        # Rewrite pruned list atomically
        pipe = self._redis.pipeline()
        pipe.delete(key)
        for m in messages:
            pipe.rpush(key, json.dumps(m))
        pipe.expire(key, self._ttl)
        await pipe.execute()

    # ------------------------------------------------------------
    # TTL Refresh
    # ------------------------------------------------------------

    async def touch(self, session_id: str) -> None:
        """
        Refresh TTL for metadata + history.
        Exported.
        """
        await self._redis.expire(f"session:{session_id}", self._ttl)
        await self._redis.expire(f"session:{session_id}:messages", self._ttl)

    # ------------------------------------------------------------
    # Session Deletion
    # ------------------------------------------------------------

    async def delete_session(self, session_id: str) -> None:
        """
        Delete all session data.
        Exported.
        """
        await self._redis.delete(f"session:{session_id}")
        await self._redis.delete(f"session:{session_id}:messages")

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    def _now(self) -> float:
        """
        Return current timestamp.
        Internal.
        """
        return time.time()

