"""
System endpoints for LLMLab Router.

Provides:
- /v1/logs     : return recent router logs
- /v1/health   : return backend + router health status
- /v1/metrics  : return Prometheus-style metrics
- /v1/stats    : return human-readable router statistics
"""

from fastapi import APIRouter, Response
from typing import Dict, Any
import time

from ..core.router_logger import RouterLogger
from ..core.backend_health import BackendHealthGate
from ..core.model_registry import ModelRegistry
from ..core.backend_factory import BackendFactory


def create_system_router(
    logger: RouterLogger,
    health_gate: BackendHealthGate,
    registry: ModelRegistry,
    backend_factory: BackendFactory,
    start_time: float,
) -> APIRouter:
    """
    Create system API router.
    Exported.
    """
    router = APIRouter()

    # ------------------------------------------------------------
    # /v1/logs
    # ------------------------------------------------------------
    @router.get("/v1/logs")
    async def get_logs() -> Dict[str, Any]:
        """
        Return recent router logs (in-memory buffer).
        Exported.
        """
        logs = await logger.get_logs()
        return {"count": len(logs), "logs": logs}

    # ------------------------------------------------------------
    # /v1/health
    # ------------------------------------------------------------
    @router.get("/v1/health")
    async def get_health() -> Dict[str, Any]:
        """
        Return router + backend health status.
        Exported.
        """
        backends = registry.list_backends()
        results = []

        for b in backends:
            adapter = backend_factory.get_adapter(b)
            healthy = await health_gate.is_healthy(adapter)

            results.append(
                {
                    "backend": b["name"],
                    "type": b["type"],
                    "base_url": b["base_url"],
                    "healthy": healthy,
                }
            )

        return {
            "router": "healthy",
            "backends": results,
        }

    # ------------------------------------------------------------
    # /v1/metrics (Prometheus)
    # ------------------------------------------------------------
    @router.get("/v1/metrics")
    async def get_metrics() -> Response:
        """
        Return Prometheus-style metrics.
        Exported.
        """
        uptime = time.time() - start_time
        backends = registry.list_backends()

        healthy_count = 0
        unhealthy_count = 0
        backend_metrics = []

        for b in backends:
            adapter = backend_factory.get_adapter(b)
            healthy = await health_gate.is_healthy(adapter)

            if healthy:
                healthy_count += 1
            else:
                unhealthy_count += 1

            backend_metrics.append(
                f'llmlab_backend_health{{backend="{b["name"]}",type="{b["type"]}"}} {1 if healthy else 0}'
            )

        logs = await logger.get_logs()
        log_count = len(logs)

        lines = [
            "# HELP llmlab_router_uptime_seconds Router uptime in seconds",
            "# TYPE llmlab_router_uptime_seconds gauge",
            f"llmlab_router_uptime_seconds {uptime}",
            "",
            "# HELP llmlab_backends_total Number of discovered backends",
            "# TYPE llmlab_backends_total gauge",
            f"llmlab_backends_total {len(backends)}",
            "",
            "# HELP llmlab_backends_healthy Number of healthy backends",
            "# TYPE llmlab_backends_healthy gauge",
            f"llmlab_backends_healthy {healthy_count}",
            "",
            "# HELP llmlab_backends_unhealthy Number of unhealthy backends",
            "# TYPE llmlab_backends_unhealthy gauge",
            f"llmlab_backends_unhealthy {unhealthy_count}",
            "",
            "# HELP llmlab_log_entries_total Number of in-memory log entries",
            "# TYPE llmlab_log_entries_total gauge",
            f"llmlab_log_entries_total {log_count}",
            "",
            "# HELP llmlab_backend_health Backend health status (1=healthy, 0=unhealthy)",
            "# TYPE llmlab_backend_health gauge",
        ]

        lines.extend(backend_metrics)

        body = "\n".join(lines) + "\n"
        return Response(content=body, media_type="text/plain")

    # ------------------------------------------------------------
    # /v1/stats (Human-readable)
    # ------------------------------------------------------------
    @router.get("/v1/stats")
    async def get_stats() -> Dict[str, Any]:
        """
        Return human-readable router statistics.
        Exported.
        """
        uptime_seconds = time.time() - start_time
        uptime_hours = round(uptime_seconds / 3600, 2)

        backends = registry.list_backends()
        backend_stats = []
        healthy_count = 0
        unhealthy_count = 0

        for b in backends:
            adapter = backend_factory.get_adapter(b)
            healthy = await health_gate.is_healthy(adapter)

            if healthy:
                healthy_count += 1
            else:
                unhealthy_count += 1

            backend_stats.append(
                {
                    "name": b["name"],
                    "type": b["type"],
                    "base_url": b["base_url"],
                    "status": "healthy" if healthy else "unhealthy",
                }
            )

        logs = await logger.get_logs()
        log_count = len(logs)

        severity_counts = {"INFO": 0, "WARN": 0, "ERROR": 0, "FATAL": 0}
        for line in logs:
            for sev in severity_counts:
                if f"[{sev}]" in line:
                    severity_counts[sev] += 1

        return {
            "router_status": "healthy",
            "uptime_hours": uptime_hours,
            "backend_summary": {
                "total_backends": len(backends),
                "healthy_backends": healthy_count,
                "unhealthy_backends": unhealthy_count,
                "details": backend_stats,
            },
            "log_summary": {
                "total_entries": log_count,
                "severity_breakdown": severity_counts,
            },
        }

    return router

