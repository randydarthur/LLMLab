# services/scrape_ollama_catalog.py

"""
Ollama Library Scraper for LLMLab (Operator‑Triggered Only)

This module performs a full scrape of the Ollama Library website and
produces a catalog structure compatible with Registry v2:

    {
        "<repo>": {
            "item_source": "ollama-library",
            "variants": {
                "<variant>": {
                    "full_tag": "...",
                    "parameters_b": ...,
                    "size_gb": ...,
                    "context_k": ...,
                    "input": "...",
                    "quantization": "...",
                }
            }
        }
    }

IMPORTANT:
  • No automatic scraping.
  • No background refresh.
  • Only executed when the operator explicitly triggers a refresh.
  • Safe for the Ollama Library (polite, rate-limited, minimal requests).
"""

from __future__ import annotations

import os
import json
import time
import requests
from bs4 import BeautifulSoup

from ollama_lab.utils.logging import log


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

BASE_URL = "https://ollama.com"
LIBRARY_URL = f"{BASE_URL}/library?sort=newest"
CATALOG_PATH = os.path.expanduser("~/.llmlab/catalog.json")

HEADERS = {"User-Agent": "LLMLab-Scraper/1.0"}

CACHE_TTL = 3600
_cache = None
_cache_ts = 0.0

DEBUG_SCRAPER = False


# ------------------------------------------------------------
# HTML fetch helper
# ------------------------------------------------------------

def fetch_html(url: str) -> str:
    if DEBUG_SCRAPER:
        log(f"[SCRAPER][DEBUG] Fetching HTML: {url}", "INFO")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        log(f"[SCRAPER] Failed to fetch {url}: {e}", "ERROR")
        raise


# ------------------------------------------------------------
# Parsing helpers
# ------------------------------------------------------------

def parse_parameters_b(full_tag: str) -> float:
    """
    Extract the "<n>b" parameter count from tags like:
        llama3:8b
        mistral:7b-instruct
    """
    try:
        tag = full_tag.split(":", 1)[1]
        first = tag.split("-", 1)[0]
        if first.endswith("b"):
            return float(first[:-1])
    except Exception:
        pass
    return 0.0


def parse_quantization(full_tag: str) -> str | None:
    """
    Extract quantization suffix from tags like:
        llama3:8b-q4
        mistral:7b-instruct-q8
    """
    try:
        tag = full_tag.split(":", 1)[1]
        parts = tag.split("-")
        if len(parts) <= 1:
            return None
        last = parts[-1]
        first = parts[0]
        if last == first:
            return None
        return last
    except Exception:
        return None


def parse_size_gb(size_str: str) -> float:
    if not size_str or size_str == "-":
        return 0.0
    try:
        if size_str.lower().endswith("gb"):
            return float(size_str[:-2])
    except Exception:
        pass
    return 0.0


def parse_context_k(context_str: str) -> int:
    if not context_str:
        return 0
    try:
        if context_str.lower().endswith("k"):
            return int(context_str[:-1])
    except Exception:
        pass
    return 0


# ------------------------------------------------------------
# LEVEL 1: Library index
# ------------------------------------------------------------

def parse_library_index():
    if DEBUG_SCRAPER:
        log("[SCRAPER][DEBUG] Parsing library index...", "INFO")

    html = fetch_html(LIBRARY_URL)
    soup = BeautifulSoup(html, "html.parser")

    models = []
    cards = soup.select("a[href^='/library/']")

    if DEBUG_SCRAPER:
        log(f"[SCRAPER][DEBUG] Found {len(cards)} library cards", "INFO")

    for card in cards:
        href = card.get("href")
        if not href:
            continue

        name = href.split("/")[-1]
        url = BASE_URL + href

        models.append({"name": name, "url": url})

    return models


# ------------------------------------------------------------
# LEVEL 2: Find "View all"
# ------------------------------------------------------------

def find_view_all_url(model_page_url: str) -> str | None:
    if DEBUG_SCRAPER:
        log(f"[SCRAPER][DEBUG] Fetching family page: {model_page_url}", "INFO")

    html = fetch_html(model_page_url)
    soup = BeautifulSoup(html, "html.parser")

    link = soup.find("a", string=lambda t: t and "View all" in t)
    if not link:
        if DEBUG_SCRAPER:
            log("[SCRAPER][DEBUG] No 'View all' link found", "WARN")
        return None

    href = link.get("href")
    if not href:
        return None

    if not href.startswith("http"):
        href = BASE_URL + href

    if DEBUG_SCRAPER:
        log(f"[SCRAPER][DEBUG] View-all URL: {href}", "INFO")

    return href


# ------------------------------------------------------------
# LEVEL 3: Parse full model table
# ------------------------------------------------------------

def parse_full_model_table(url: str):
    if DEBUG_SCRAPER:
        log(f"[SCRAPER][DEBUG] Parsing full model table: {url}", "INFO")

    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    variants = []
    blocks = soup.select("div.group.px-4.py-3")

    if DEBUG_SCRAPER:
        log(f"[SCRAPER][DEBUG] Found {len(blocks)} variant blocks", "INFO")

    for block in blocks:
        desktop = block.select_one("div.hidden.md\\:flex")
        if not desktop:
            continue

        grid = desktop.select_one("div.grid.grid-cols-12")
        if not grid:
            continue

        name_span = grid.select_one("span.col-span-6 a")
        if not name_span:
            continue

        full_tag = name_span.get_text(strip=True)

        # Skip cloud-only entries
        if "cloud" in full_tag.lower():
            if DEBUG_SCRAPER:
                log(f"[SCRAPER][DEBUG] Skipping cloud-only: {full_tag}", "INFO")
            continue

        size_col = grid.select_one("p.col-span-2")
        context_cols = grid.select("p.col-span-2")
        input_col = grid.select_one("div.col-span-2")

        size_text = size_col.get_text(strip=True) if size_col else ""
        context_text = context_cols[1].get_text(strip=True) if len(context_cols) > 1 else ""
        input_text = input_col.get_text(strip=True) if input_col else ""

        row = {
            "full_tag": full_tag,
            "parameters_b": parse_parameters_b(full_tag),
            "size_gb": parse_size_gb(size_text),
            "context_k": parse_context_k(context_text),
            "input": input_text,
            "quantization": parse_quantization(full_tag),
        }

        if DEBUG_SCRAPER:
            log(f"[SCRAPER][DEBUG] Parsed row: {row}", "INFO")

        variants.append(row)

    return variants


# ------------------------------------------------------------
# Full scrape (dict-of-dicts output)
# ------------------------------------------------------------

def scrape_full_catalog(force_refresh: bool = False):
    global _cache, _cache_ts

    now = time.time()
    if not force_refresh and _cache and (now - _cache_ts < CACHE_TTL):
        if DEBUG_SCRAPER:
            log("[SCRAPER][DEBUG] Using cached catalog", "INFO")
        return _cache

    log("[SCRAPER] Fetching Ollama library index...", "INFO")
    index = parse_library_index()

    if DEBUG_SCRAPER:
        log(f"[SCRAPER][DEBUG] Library index contains {len(index)} families", "INFO")

    catalog = {}

    for idx, entry in enumerate(index):
        name = entry["name"]

        if DEBUG_SCRAPER:
            log(f"[SCRAPER][DEBUG] Processing family {idx+1}: {name}", "INFO")

        # Debug mode: limit scrape for faster iteration
        if DEBUG_SCRAPER and idx >= 5:
            log("[SCRAPER][DEBUG] Debug mode active: stopping after 5 families", "INFO")
            break

        view_all_url = find_view_all_url(entry["url"])
        if not view_all_url:
            log(f"[SCRAPER] No 'View all' page for {name}", "WARN")
            continue

        variants = parse_full_model_table(view_all_url)
        if not variants:
            log(f"[SCRAPER] Skipping {name}: no downloadable variants", "WARN")
            continue

        # Convert list → dict keyed by variant name
        variant_dict = {}
        for v in variants:
            full_tag = v["full_tag"]
            variant_name = full_tag.split(":", 1)[1]
            variant_dict[variant_name] = v

        catalog[name] = {
            "item_source": "ollama-library",
            "variants": variant_dict,
        }

    _cache = catalog
    _cache_ts = now

    log(f"[SCRAPER] Scraped {len(catalog)} model families", "INFO")
    return catalog


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

def main():
    try:
        log("[Catalog] Refresh requested by operator.", "INFO")

        # 1. Scrape full catalog
        catalog = scrape_full_catalog(force_refresh=True)

        # 2. Write catalog.json (debugging / external use)
        os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
        with open(CATALOG_PATH, "w") as f:
            json.dump(catalog, f, indent=2)
        log(f"[Catalog] Wrote catalog file to {CATALOG_PATH}", "INFO")

        # 3. Load into registry
        from ollama_lab.services.registry import (
            update_catalog,
            set_catalog_last_refreshed,
        )

        update_catalog(catalog)
        set_catalog_last_refreshed(time.time())

        log("[Catalog] Registry updated with new catalog.", "INFO")
        return 0

    except Exception as e:
        log(f"[Catalog] Refresh failed: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    exit(main())

