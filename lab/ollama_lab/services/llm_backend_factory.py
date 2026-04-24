# services/llm_backend_factory.py

from __future__ import annotations

"""
Unified LLM Backend Factory for LLMLab (Full‑Tag Architecture)

LLMLab v2 uses a single local backend: Ollama.

This module provides:
  • A clean abstract backend interface
  • A concrete OllamaBackend implementation
  • A cached backend instance via get_llm_backend()

Backend selection is intentionally simple:
  - Only Ollama is supported today
  - Detection is environment‑aware but defaults to Ollama
"""

import os
import sys
import subprocess
import time

from ollama_lab.utils.logging import log

# Import Ollama client functions (backend‑agnostic)
from ollama_lab.services.ollama_client import (
    is_available as ollama_available,
    ensure_available as ollama_ensure,
    list_models as ollama_list_models,
    model_exists as ollama_model_exists,
    pull_model as ollama_pull_model,
    delete_model as ollama_delete_model,
    generate_stream as ollama_generate_stream,
    generate as ollama_generate,
    embed as ollama_embed,
)


# ============================================================
# Abstract Backend Interface
# ============================================================

class LLMBackend:
    """Abstract interface for all local LLM backends."""

    # --- Availability ---
    def is_available(self) -> bool: ...
    def ensure_available(self) -> None: ...

    # --- Model Management ---
    def list_models(self): ...
    def model_exists(self, full_tag: str) -> bool: ...
    def pull_model(self, full_tag: str) -> None: ...
    def delete_model(self, full_tag: str) -> None: ...

    # --- Generation ---
    def generate_stream(self, full_tag: str, prompt: str, **kwargs): ...
    def generate(self, full_tag: str, prompt: str, **kwargs) -> str: ...

    # --- Embeddings ---
    def embed(self, full_tag: str, text: str): ...

    # --- Daemon Lifecycle ---
    def daemon_status(self) -> bool: ...
    def start_daemon(self) -> None: ...
    def stop_daemon(self) -> None: ...


# ============================================================
# Ollama Backend Implementation
# ============================================================

class OllamaBackend(LLMBackend):
    """Unified Ollama backend for LLMLab v2."""

    def __init__(self):
        # Exponential backoff state
        self._fail_count = 0
        self._last_fail_ts = 0.0
        self._max_backoff = 600  # 10 minutes

    # -------------------------
    # Availability (with exponential cooldown)
    # -------------------------

    def is_available(self) -> bool:
        now = time.time()

        # If we recently failed, apply exponential backoff
        if self._fail_count > 0:
            delay = min(2 ** (self._fail_count - 1), self._max_backoff)
            if now - self._last_fail_ts < delay:
                return False

        # Try contacting Ollama
        try:
            ok = ollama_available()
            if ok:
                # Reset cooldown on success
                self._fail_count = 0
                return True

            # Failure path
            self._fail_count += 1
            self._last_fail_ts = now
            return False

        except Exception:
            # Hard failure: increase backoff
            self._fail_count += 1
            self._last_fail_ts = now
            return False

    def ensure_available(self) -> None:
        return ollama_ensure()

    # -------------------------
    # Model Management
    # -------------------------

    def list_models(self):
        return ollama_list_models()

    def model_exists(self, full_tag: str) -> bool:
        return ollama_model_exists(full_tag)

    def pull_model(self, full_tag: str) -> None:
        return ollama_pull_model(full_tag)

    def delete_model(self, full_tag: str) -> None:
        return ollama_delete_model(full_tag)

    # -------------------------
    # Generation
    # -------------------------

    def generate_stream(self, full_tag: str, prompt: str, **kwargs):
        return ollama_generate_stream(full_tag, prompt, **kwargs)

    def generate(self, full_tag: str, prompt: str, **kwargs) -> str:
        return ollama_generate(full_tag, prompt, **kwargs)

    # -------------------------
    # Embeddings
    # -------------------------

    def embed(self, full_tag: str, text: str):
        return ollama_embed(full_tag, text)

    # ============================================================
    # Daemon Lifecycle (Unified)
    # ============================================================

    def daemon_status(self) -> bool:
        return self.is_available()

    def _brew_path(self) -> str:
        """Return the correct brew path on macOS."""
        for path in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
            if os.path.exists(path):
                return path
        return "brew"

    def start_daemon(self) -> None:
        platform = sys.platform

        try:
            if platform.startswith("darwin"):
                subprocess.run([self._brew_path(), "services", "start", "ollama"], check=True)

            elif platform.startswith("linux"):
                subprocess.run(["systemctl", "start", "ollama"], check=True)

            elif platform.startswith("win"):
                subprocess.run(["sc", "start", "Ollama"], check=True)

            else:
                raise RuntimeError(f"Unsupported platform for daemon control: {platform}")

            log("[OllamaBackend] Daemon start command issued.", "INFO")

        except Exception as e:
            raise RuntimeError(f"Failed to start Ollama daemon: {e}")

    def stop_daemon(self) -> None:
        platform = sys.platform

        try:
            if platform.startswith("darwin"):
                subprocess.run([self._brew_path(), "services", "stop", "ollama"], check=True)

            elif platform.startswith("linux"):
                subprocess.run(["systemctl", "stop", "ollama"], check=True)

            elif platform.startswith("win"):
                subprocess.run(["sc", "stop", "Ollama"], check=True)

            else:
                raise RuntimeError(f"Unsupported platform for daemon control: {platform}")

            log("[OllamaBackend] Daemon stop command issued.", "INFO")

        except Exception as e:
            raise RuntimeError(f"Failed to stop Ollama daemon: {e}")


# ============================================================
# Backend Selection (Optimized)
# ============================================================

_cached_backend: LLMBackend | None = None
_logged_backend_choice = False


def _detect_backend_name() -> str:
    """
    Detect backend name from environment or availability.
    Currently only Ollama is supported.
    """
    env_choice = os.environ.get("LLMLAB_BACKEND")
    if env_choice:
        return env_choice.lower().strip()

    if ollama_available():
        return "ollama"

    return "ollama"  # fallback


def get_llm_backend() -> LLMBackend:
    """
    Return a cached backend instance.
    Log backend selection only once.
    """
    global _cached_backend
    global _logged_backend_choice

    if _cached_backend is not None:
        return _cached_backend

    backend_name = _detect_backend_name()

    backend = OllamaBackend()

    if not _logged_backend_choice:
        log(f"[llm_backend_factory] Using backend: {backend_name}", "INFO")
        _logged_backend_choice = True

    _cached_backend = backend
    return backend

