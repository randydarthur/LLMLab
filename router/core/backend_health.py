"""
Backend health-check gating layer for the LLMLab LLM Router.

Responsibilities:
- Track backend health status
- Cache health results with TTL
- Track consecutive failures
- Apply exponential backoff
- Provide a safe lookup API for RoutingEngine
"""

from typing import Dict, Any
import time
import math

from ..backends.base import BackendAdapter


class BackendHealthGate:
    """
    Health-check gate that ensures RoutingEngine only uses healthy backends.
    Exported.
    """

    def __init__(self, ttl_seconds: int = 10, max_failures: int = 3):
        self._ttl = ttl_seconds
        self._max_failures = max_failures

        # Cache structure:
        # {
        #   backend_name: {
        #       "healthy": bool,
        #       "timestamp": float,
        #       "failures": int,
        #       "backoff_until": float
        #   }
        # }
        self._cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    async def is_healthy(self, adapter: BackendAdapter) -> bool:
        """
        Return True if backend is healthy (cached or freshly checked).
        Applies exponential backoff after repeated failures.
        Exported.
        """
        name = adapter.name
        now = time.time()

        entry = self._cache.get(name)

        # ------------------------------------------------------------
        # 1. Backoff check
        # ------------------------------------------------------------
        if entry and entry.get("backoff_until", 0) > now:
            return False

        # ------------------------------------------------------------
        # 2. TTL cache check
        # ------------------------------------------------------------
        if entry and (now - entry["timestamp"] < self._ttl):
            return entry["healthy"]

        # ------------------------------------------------------------
        # 3. Fresh health check
        # ------------------------------------------------------------
        healthy = await adapter.is_available()

        if not entry:
            entry = {"failures": 0, "backoff_until": 0}

        if healthy:
            entry["healthy"] = True
            entry["timestamp"] = now
            entry["failures"] = 0
            entry["backoff_until"] = 0
        else:
            entry["healthy"] = False
            entry["timestamp"] = now
            entry["failures"] += 1

            # Exponential backoff
            if entry["failures"] >= self._max_failures:
                backoff_seconds = min(60, 2 ** entry["failures"])
                entry["backoff_until"] = now + backoff_seconds

        self._cache[name] = entry
        return healthy

    async def get_healthy_adapter(self, adapter: BackendAdapter) -> BackendAdapter:
        """
        Return adapter if healthy, else raise.
        Exported.
        """
        if await self.is_healthy(adapter):
            return adapter

        raise RuntimeError(f"Backend '{adapter.name}' is unhealthy or in backoff")

