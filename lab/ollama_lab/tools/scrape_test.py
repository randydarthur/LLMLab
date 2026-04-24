# ollama_lab/tools/scrape_test.py

"""
Scraper diagnostic utility for LLMLab.

This version:
  • Calls the REAL scraper module directly (no subprocess)
  • Prints full traceback on failure
  • Prints success message and catalog size on success
  • Helps debug scraper crashes that appear as exit code 1 in the TUI
"""

import traceback
import json
import os

from ollama_lab.utils.logging import log
from ollama_lab.services import scrape_ollama_catalog


CATALOG_PATH = os.path.expanduser("~/.llmlab/catalog.json")


def main():
    log("[SCRAPE_TEST] Starting REAL scraper test...", "INFO")
    print("\n====================================================")
    print("RUNNING REAL SCRAPER (services/scrape_ollama_catalog.py)")
    print("====================================================\n")

    try:
        # Call the real scraper entrypoint
        scrape_ollama_catalog.main()
        print("\n[SUCCESS] Scraper completed without throwing.")
    except Exception as e:
        print("\n[ERROR] Scraper threw an exception:")
        print("----------------------------------------------------")
        traceback.print_exc()
        print("----------------------------------------------------")
        print("This is the root cause of the TUI refresh failure.")
        return

    # After scraper runs, inspect the catalog file
    print("\n====================================================")
    print("Inspecting generated catalog file...")
    print("====================================================")

    if not os.path.exists(CATALOG_PATH):
        print(f"[ERROR] Catalog file not found at: {CATALOG_PATH}")
        return

    try:
        with open(CATALOG_PATH, "r") as f:
            data = json.load(f)
        print(f"[OK] Catalog loaded. Total repos: {len(data)}")
    except Exception as e:
        print(f"[ERROR] Failed to load catalog JSON: {e}")
        traceback.print_exc()
        return

    print("\n====================================================")
    print("Scrape test complete.")
    print("====================================================")


if __name__ == "__main__":
    main()

