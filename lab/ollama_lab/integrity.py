# models/integrity.py
#
# Unified-backend model integrity checker.
# Performs:
#   1. Registry + backend existence checks
#   2. Loadability probe
#   3. Optional generation + embedding checks
#   4. Returns structured results for the TUI to display

from __future__ import annotations

from ollama_lab.services.llm_backend_factory import get_llm_backend
from ollama_lab.services.registry import get_model
from ollama_lab.tui.widgets import modal_message

from ollama_lab.models.validation import (
    validate_registry_entry,
    validate_backend_availability,
    validate_model_exists,
    validate_model_loadable,
    validate_generation,
    validate_embeddings,
)


def verify_model_integrity(stdscr, repo: str):
    """
    Perform unified integrity checking:
      - Validate registry entry
      - Validate backend availability
      - Validate model exists on backend
      - Validate model loadability
      - Optional generation + embedding checks
      - Display results in a modal
    """

    repo = repo.strip().lower()
    entry = get_model(repo)

    if not entry:
        modal_message(stdscr, [f"Unknown model: {repo}"])
        return

    full_tag = entry["full_tag"]

    results = []  # (label, success, message)

    # ------------------------------------------------------------
    # 1. Registry entry validation
    # ------------------------------------------------------------
    ok = validate_registry_entry(repo)
    results.append(("Registry entry", ok, "OK" if ok else "Invalid registry entry"))
    if not ok:
        return _show_results(stdscr, repo, results)

    # ------------------------------------------------------------
    # 2. Backend availability
    # ------------------------------------------------------------
    ok = validate_backend_availability()
    results.append(("Backend availability", ok, "OK" if ok else "Backend unreachable"))
    if not ok:
        return _show_results(stdscr, repo, results)

    # ------------------------------------------------------------
    # 3. Model exists on backend
    # ------------------------------------------------------------
    ok = validate_model_exists(repo)
    results.append(("Model exists", ok, "OK" if ok else "Model missing on backend"))
    if not ok:
        return _show_results(stdscr, repo, results)

    # ------------------------------------------------------------
    # 4. Loadability probe (tiny generation)
    # ------------------------------------------------------------
    ok = validate_model_loadable(repo)
    results.append(("Loadability", ok, "OK" if ok else "Model failed to load"))
    if not ok:
        return _show_results(stdscr, repo, results)

    # ------------------------------------------------------------
    # 5. Optional functional checks
    # ------------------------------------------------------------
    ok = validate_generation(repo)
    results.append(("Minimal generate", ok, "OK" if ok else "Generation failed"))

    ok = validate_embeddings(repo)
    results.append(("Minimal embed", ok, "OK" if ok else "Embedding failed"))

    # ------------------------------------------------------------
    # 6. Display results
    # ------------------------------------------------------------
    return _show_results(stdscr, repo, results)


# ------------------------------------------------------------
# Helper — display results in a modal
# ------------------------------------------------------------

def _show_results(stdscr, repo: str, results):
    all_ok = all(success for (_, success, _) in results)

    if all_ok:
        modal_message(
            stdscr,
            [
                f"INTEGRITY OK — {repo}",
                "All checks passed successfully.",
            ],
        )
        return

    lines = [
        f"INTEGRITY CHECK — {repo}",
        "────────────────────────",
    ]

    for label, success, msg in results:
        if success:
            lines.append(f"✓ {label} OK")
        else:
            lines.append(f"✗ {label} failed: {msg}")

    modal_message(stdscr, lines)

