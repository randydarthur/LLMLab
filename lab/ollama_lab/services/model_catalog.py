# services/model_catalog.py

"""
Model Catalog Service for LLMLab (Registry‑Backed, Full‑Tag Architecture)

This module provides a clean interface for:
  • Listing catalog repos and variants
  • Listing downloadable repos/variants
  • Looking up catalog metadata
  • Checking installed state (registry v2)
  • Refreshing the catalog (explicit operator action only)

The catalog is stored in registry["catalog"] and populated by:
  - scrape_ollama_catalog.py (item_source="ollama-library")
  - local/custom additions (item_source="local"/"custom")

This module contains **no automatic scraping logic**.
Catalog refresh happens ONLY when explicitly triggered.
"""

from __future__ import annotations

import subprocess
from typing import Dict, List, Optional

from ollama_lab.services.registry import (
    get_catalog,
    list_installed,
)

from ollama_lab.utils.logging import log


# ------------------------------------------------------------
# Catalog access
# ------------------------------------------------------------

def list_catalog_repos() -> List[str]:
    catalog = get_catalog()
    return sorted(catalog.keys())


def get_catalog_entry(repo: str) -> Optional[Dict]:
    return get_catalog().get(repo)


def list_variants(repo: str) -> List[str]:
    entry = get_catalog_entry(repo)
    if not entry:
        return []
    variants = entry.get("variants") or {}
    return sorted(variants.keys())


def get_variant_metadata(repo: str, variant: str) -> Optional[Dict]:
    entry = get_catalog_entry(repo)
    if not entry:
        return None
    variants = entry.get("variants") or {}
    return variants.get(variant)


# ------------------------------------------------------------
# Installed state helpers (Registry v2)
# ------------------------------------------------------------

def _installed_composite_key(repo: str, variant: str, item_source: str) -> str:
    return f"{repo}:{variant}|{item_source}"


def is_variant_installed(repo: str, variant: str) -> bool:
    """
    Determine installed state using registry v2 composite keys.
    """
    entry = get_catalog_entry(repo)
    if not entry:
        return False

    item_source = entry.get("item_source", "unknown")
    key = _installed_composite_key(repo, variant, item_source)

    installed = list_installed()
    return key in installed


def find_installed_variants(repo: str) -> List[str]:
    """
    Return a list of installed variants for a given repo.
    Uses registry v2 composite keys.
    """
    entry = get_catalog_entry(repo)
    if not entry:
        return []

    item_source = entry.get("item_source", "unknown")
    installed = list_installed()

    prefix = f"{repo}:"
    suffix = f"|{item_source}"

    variants = []
    for key in installed.keys():
        if key.startswith(prefix) and key.endswith(suffix):
            variant = key[len(prefix): -len(suffix)]
            variants.append(variant)

    return sorted(variants)


# ------------------------------------------------------------
# Downloadable models
# ------------------------------------------------------------

def list_downloadable_repos() -> List[str]:
    """
    A repo is downloadable if it has at least one variant
    that is NOT installed.
    """
    repos = list_catalog_repos()
    downloadable = []

    for repo in repos:
        variants = list_variants(repo)
        installed_variants = set(find_installed_variants(repo))

        if any(v not in installed_variants for v in variants):
            downloadable.append(repo)

    return sorted(downloadable)


def list_downloadable_variants(repo: str) -> List[str]:
    """
    Return variants for a repo that are NOT installed.
    """
    variants = list_variants(repo)
    installed_variants = set(find_installed_variants(repo))
    return sorted([v for v in variants if v not in installed_variants])


# ------------------------------------------------------------
# Catalog refresh + empty check
# ------------------------------------------------------------

def is_catalog_empty() -> bool:
    """
    Return True if the catalog has no repos.
    Used on startup to seed the catalog once.
    """
    catalog = get_catalog()
    return not bool(catalog)


def refresh_catalog() -> None:
    """
    Explicit operator-triggered catalog refresh.
    Runs scrape_ollama_catalog.py and reloads the catalog.

    IMPORTANT:
    - No automatic refreshes.
    - No timers.
    - No background scraping.
    - Safe for Ollama Library (operator-controlled only).
    """
    log("[Catalog] Refresh requested by operator.", "INFO")

    try:
        subprocess.run(
            ["python3", "-m", "ollama_lab.services.scrape_ollama_catalog"],
            check=True,
        )
    except Exception as e:
        log(f"[Catalog] Refresh failed: {e}", "ERROR")
        raise

    log("[Catalog] Refresh completed successfully.", "INFO")


def load_catalog() -> Dict:
    """
    Reload the catalog from registry.
    Provided for completeness; main.py uses get_catalog() directly.
    """
    return get_catalog()


# ------------------------------------------------------------
# Full catalog listing for TUI
# ------------------------------------------------------------

def list_catalog_with_install_state() -> List[Dict]:
    """
    Return a structured list of repos + variants + install state
    for use in the TUI.
    """
    catalog = get_catalog()
    installed = list_installed()

    results = []

    for repo, entry in catalog.items():
        item_source = entry.get("item_source", "unknown")
        variants = entry.get("variants") or {}

        variant_list = []
        for variant, metadata in variants.items():
            key = f"{repo}:{variant}|{item_source}"
            variant_list.append({
                "variant": variant,
                "installed": key in installed,
                "metadata": metadata,
            })

        results.append({
            "name": repo,
            "item_source": item_source,
            "variants": sorted(variant_list, key=lambda v: v["variant"]),
        })

    return sorted(results, key=lambda e: e["name"])

