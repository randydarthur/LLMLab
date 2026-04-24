"""
Registry management for LLMLab (Registry v2 + Full‑Tag Architecture).

This module is intentionally backend‑agnostic.
It never imports or constructs a backend. The caller must pass a backend
instance into rebuild_registry_from_backend().

Registry v2 Responsibilities:
  • Load and save registry.json
  • Maintain catalog entries (scraped, local, custom)
  • Maintain installed entries (backend truth)
  • Link installed variants to catalog entries via composite keys
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, Any

from ollama_lab.utils.logging import log


# ------------------------------------------------------------
# Registry file location
# ------------------------------------------------------------

REGISTRY_PATH = os.path.expanduser("~/.llmlab/registry.json")


# ------------------------------------------------------------
# Low‑level persistence
# ------------------------------------------------------------

def load_registry() -> Dict[str, Any]:
    """
    Load registry.json. If missing or invalid, return a default structure.
    """
    if not os.path.exists(REGISTRY_PATH):
        return {"catalog": {}, "installed": {}, "settings": {}}

    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("catalog", {})
            data.setdefault("installed", {})
            data.setdefault("settings", {})
            return data
    except Exception as e:
        log(f"[REGISTRY] Failed to load registry: {e}", "ERROR")
        return {"catalog": {}, "installed": {}, "settings": {}}


def save_registry(data: Dict[str, Any]) -> None:
    """
    Save registry.json, creating parent directory if needed.
    """
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)

    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"[REGISTRY] Failed to save registry: {e}", "ERROR")


# ------------------------------------------------------------
# Settings helpers
# ------------------------------------------------------------

def get_settings() -> Dict[str, Any]:
    data = load_registry()
    settings = data.get("settings") or {}
    data["settings"] = settings
    save_registry(data)
    return settings


def update_settings(new_settings: Dict[str, Any]) -> None:
    data = load_registry()
    settings = data.get("settings") or {}
    settings.update(new_settings)
    data["settings"] = settings
    save_registry(data)


DEFAULT_LOG_HISTORY_LINES = 5000


def set_settings(new_settings: Dict[str, Any]) -> None:
    data = load_registry()
    data["settings"] = new_settings
    save_registry(data)


def get_log_history_lines() -> int | None:
    return get_settings().get("log_history_lines")


def set_log_history_lines(n: int) -> None:
    if not isinstance(n, int) or n <= 0:
        raise ValueError("log_history_lines must be a positive integer")

    data = load_registry()
    settings = data.get("settings") or {}
    settings["log_history_lines"] = n
    data["settings"] = settings
    save_registry(data)


# ------------------------------------------------------------
# Catalog refresh timestamp helpers
# ------------------------------------------------------------

def get_catalog_last_refreshed() -> float | None:
    return get_settings().get("catalog_last_refreshed")


def set_catalog_last_refreshed(ts: float) -> None:
    data = load_registry()
    settings = data.get("settings") or {}
    settings["catalog_last_refreshed"] = ts
    data["settings"] = settings
    save_registry(data)


# ------------------------------------------------------------
# Catalog helpers
# ------------------------------------------------------------

def get_catalog() -> Dict[str, Any]:
    return load_registry().get("catalog", {})


def update_catalog(new_catalog_entries: Dict[str, Any]) -> None:
    """
    Merge new catalog entries into registry["catalog"].
    Local/custom entries are preserved and never overwritten.
    """
    data = load_registry()
    catalog = data.get("catalog", {})

    for repo, entry in new_catalog_entries.items():
        source = entry.get("item_source")

        # Never overwrite local/custom entries
        if repo in catalog:
            existing_source = catalog[repo].get("item_source")
            if existing_source in ("local", "custom"):
                continue

        catalog[repo] = entry

    data["catalog"] = catalog
    save_registry(data)


# ------------------------------------------------------------
# Installed helpers
# ------------------------------------------------------------

def list_installed() -> Dict[str, Any]:
    return load_registry().get("installed", {})


def get_installed(key: str) -> Dict[str, Any] | None:
    return list_installed().get(key)


# ------------------------------------------------------------
# Registry rebuild (backend‑agnostic)
# ------------------------------------------------------------

def rebuild_registry_from_backend(backend) -> None:
    """
    Rebuild registry["installed"] from backend truth.

    Installed entries are keyed by:
        "<full_tag>|<item_source>"

    item_source is derived from catalog:
        - "scraped" for catalog entries
        - "local" for models not in catalog
        - "custom" for user-defined entries
    """

    if backend is None:
        raise ValueError(
            "rebuild_registry_from_backend() requires a backend instance. "
            "Registry must not import or construct backends."
        )

    try:
        backend_models = backend.list_models()
    except Exception as e:
        raise RuntimeError(f"Failed to query backend for model list: {e}")

    data = load_registry()
    catalog = data.get("catalog", {})
    installed = data.get("installed", {})

    seen_keys = set()

    for m in backend_models:
        full_tag = m.get("name")
        if not isinstance(full_tag, str) or ":" not in full_tag:
            continue

        repo, variant = full_tag.split(":", 1)

        # Determine item_source
        catalog_entry = catalog.get(repo)
        if catalog_entry:
            item_source = catalog_entry.get("item_source", "scraped")
        else:
            item_source = "local"

        composite_key = f"{full_tag}|{item_source}"
        seen_keys.add(composite_key)

        installed_entry = installed.get(composite_key, {})
        installed_entry.update({
            "repo": repo,
            "variant": variant,
            "item_source": item_source,
            "full_tag": full_tag,
            "installed_at": installed_entry.get("installed_at")
                or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "alias": installed_entry.get("alias"),
        })

        installed[composite_key] = installed_entry

    # Remove stale entries
    for key in list(installed.keys()):
        if key not in seen_keys:
            del installed[key]

    data["installed"] = installed
    save_registry(data)

    log(f"[REGISTRY] Rebuilt installed registry: {len(installed)} models", "INFO")

