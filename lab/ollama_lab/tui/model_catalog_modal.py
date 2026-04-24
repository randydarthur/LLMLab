# tui/model_catalog_modal.py

import curses
import psutil

from ollama_lab.services.model_catalog import (
    list_catalog_repos,
    list_variants,
    list_downloadable_repos,
    list_downloadable_variants,
    get_variant_metadata,
)

from ollama_lab.services.llm_backend_factory import get_llm_backend
from ollama_lab.services.registry import rebuild_registry_from_backend
from ollama_lab.utils.logging import log

from ollama_lab.models.validation import (
    validate_model_loadable,
    validate_generation,
    validate_embeddings,
)


# ============================================================
# Hardware Suitability Heuristic
# ============================================================

QUANT_WEIGHTS = {
    "Q8_0": 1.00,
    "Q6_K": 0.85,
    "Q5_K_M": 0.75,
    "Q4_K_M": 0.60,
    "Q3_K_M": 0.45,
    "FP8": 1.20,
}

def classify_ram_usage(pct: float) -> str:
    if pct < 40:
        return "🟢 Good"
    if pct < 75:
        return "🟡 Fair"
    if pct < 90:
        return "🟠 Marginal"
    return "🔴 Too Tight"


def estimate_ram_usage_gb(parameters_b: float, quant: str) -> float:
    weight = QUANT_WEIGHTS.get(quant, 1.0)
    scaling = 0.55  # empirical from LLMFIT samples
    return parameters_b * weight * scaling


def suitability_for_model(meta: dict) -> tuple[str, float]:
    total_ram_gb = psutil.virtual_memory().total / (1024**3)

    params = meta.get("parameters_b")
    quant = meta.get("quantization")

    if not params or not quant:
        return ("Unknown", 0.0)

    est_ram = estimate_ram_usage_gb(float(params), quant)
    pct = (est_ram / total_ram_gb) * 100
    rating = classify_ram_usage(pct)

    return rating, pct


# ============================================================
# Color Mapping
# ============================================================

def _init_colors():
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)

    return {
        "🟢": curses.color_pair(1),
        "🟡": curses.color_pair(2),
        "🟠": curses.color_pair(3),
        "🔴": curses.color_pair(4),
    }


def _color_for_rating(rating: str, color_map):
    if not rating:
        return 0
    prefix = rating[0]
    return color_map.get(prefix, 0)


# ============================================================
# Main Catalog Modal
# ============================================================

def open_model_catalog_modal(stdscr):
    """
    Scrollable catalog browser.
    ENTER = install selected variant
    ESC   = exit
    """

    backend = get_llm_backend()
    color_map = _init_colors()

    repos = list_catalog_repos()
    if not repos:
        return _show_message(stdscr, "Catalog is empty. Run scraper first.")

    downloadable_repos = set(list_downloadable_repos())

    selected_repo = 0
    selected_variant = 0

    height, width = stdscr.getmaxyx()

    modal_h = height - 6
    modal_w = width - 10
    modal_y = 3
    modal_x = 5

    win = curses.newwin(modal_h, modal_w, modal_y, modal_x)
    win.keypad(True)

    while True:
        win.clear()
        win.border()

        title = " Model Catalog "
        win.addstr(0, (modal_w - len(title)) // 2, title, curses.A_BOLD)

        # Left pane: repos
        left_w = modal_w // 3
        right_w = modal_w - left_w - 3

        win.addstr(1, 2, "Repos", curses.A_BOLD)

        visible_repos = repos
        for idx, repo in enumerate(visible_repos):
            y = idx + 3
            if y >= modal_h - 3:
                break

            marker = "*" if repo in downloadable_repos else " "
            line = f"{marker} {repo}"

            if idx == selected_repo:
                win.addstr(y, 2, line, curses.A_REVERSE)
            else:
                win.addstr(y, 2, line)

        # Right pane: variants
        repo = repos[selected_repo]
        variants = list_variants(repo)
        downloadable_variants = set(list_downloadable_variants(repo))

        win.addstr(1, left_w + 3, f"Variants for {repo}", curses.A_BOLD)

        for idx, variant in enumerate(variants):
            y = idx + 3
            if y >= modal_h - 3:
                break

            meta = get_variant_metadata(repo, variant) or {}
            rating, pct = suitability_for_model(meta)
            color = _color_for_rating(rating, color_map)

            marker = "*" if variant in downloadable_variants else " "
            line = f"{marker} {variant}"

            if idx == selected_variant:
                win.addstr(y, left_w + 3, line, curses.A_REVERSE | color)
            else:
                win.addstr(y, left_w + 3, line, color)

        # Metadata panel
        if variants:
            variant = variants[selected_variant]
            meta = get_variant_metadata(repo, variant) or {}

            meta_y = modal_h - 10
            if meta_y > 2:
                win.addstr(meta_y, 2, "Metadata:", curses.A_BOLD)
                win.addstr(meta_y + 1, 4, f"Parameters: {meta.get('parameters_b', '?')}B")
                win.addstr(meta_y + 2, 4, f"Size:       {meta.get('size_gb', '?')}GB")
                win.addstr(meta_y + 3, 4, f"Context:    {meta.get('context_k', '?')}K")
                win.addstr(meta_y + 4, 4, f"Quant:      {meta.get('quantization', 'None')}")

                rating, pct = suitability_for_model(meta)
                win.addstr(meta_y + 6, 2, "Suitability:", curses.A_BOLD)
                win.addstr(meta_y + 7, 4, f"{rating}  ({pct:.1f}% RAM)")

        footer = "↑/↓ repo   ←/→ variant   ENTER install   ESC back"
        win.addstr(modal_h - 2, (modal_w - len(footer)) // 2, footer)

        win.refresh()

        key = win.getch()

        # Repo navigation
        if key in (curses.KEY_UP, ord('k')):
            if selected_repo > 0:
                selected_repo -= 1
                selected_variant = 0

        elif key in (curses.KEY_DOWN, ord('j')):
            if selected_repo < len(repos) - 1:
                selected_repo += 1
                selected_variant = 0

        # Variant navigation
        elif key in (curses.KEY_LEFT, ord('h')):
            if selected_variant > 0:
                selected_variant -= 1

        elif key in (curses.KEY_RIGHT, ord('l')):
            if selected_variant < len(variants) - 1:
                selected_variant += 1

        # Install selected variant
        elif key in (10, 13):  # ENTER
            if not variants:
                _show_message(stdscr, "No variants available.")
                continue

            variant = variants[selected_variant]
            full_tag = f"{repo}:{variant}"
            meta = get_variant_metadata(repo, variant) or {}

            if variant not in downloadable_variants:
                _show_message(stdscr, f"Variant {full_tag} is already installed.")
                continue

            rating, pct = suitability_for_model(meta)
            if not _confirm_install(stdscr, full_tag, rating, pct):
                continue

            _show_message(stdscr, f"Installing {full_tag}...")

            try:
                backend.pull_model(full_tag)
                log(f"[MODEL_CATALOG] Installed {full_tag}", "INFO")
            except Exception as e:
                _show_message(stdscr, f"Failed: {e}")
                return

            try:
                rebuild_registry_from_backend(backend)
            except Exception as e:
                _show_message(
                    stdscr,
                    f"Installed {full_tag}, but registry rebuild failed: {e}"
                )
                return

            load_ok = validate_model_loadable(full_tag)
            gen_ok = validate_generation(full_tag)
            emb_ok = validate_embeddings(full_tag)

            if load_ok and gen_ok and emb_ok:
                _show_message(stdscr, f"Installed {full_tag} successfully.")
            else:
                _show_message(
                    stdscr,
                    f"{full_tag} installed but failed validation. It may require repair."
                )

            return

        elif key in (27, ord('q')):
            return


# ============================================================
# Helper Modals
# ============================================================

def _show_message(stdscr, msg):
    h, w = stdscr.getmaxyx()
    win_h = 7
    win_w = max(len(msg) + 10, 30)
    win_y = (h - win_h) // 2
    win_x = (w - win_w) // 2

    win = curses.newwin(win_h, win_w, win_y, win_x)
    win.border()
    win.addstr(2, (win_w - len(msg)) // 2, msg)
    win.addstr(4, (win_w - 20) // 2, "Press any key...")
    win.refresh()
    win.getch()


def _confirm_install(stdscr, full_tag: str, rating: str, pct: float) -> bool:
    lines = [
        f"Hardware Suitability Check",
        f"Model: {full_tag}",
        "",
        f"Estimated RAM Usage: {pct:.1f}%",
        f"Rating: {rating}",
        "",
        "Proceed with installation?",
        "[Y] Yes   [N] No",
    ]

    h, w = stdscr.getmaxyx()
    win_h = len(lines) + 4
    win_w = max(max(len(line) for line in lines) + 6, 40)
    win_y = (h - win_h) // 2
    win_x = (w - win_w) // 2

    win = curses.newwin(win_h, win_w, win_y, win_x)
    win.border()

    for i, line in enumerate(lines):
        win.addstr(1 + i, 3, line)

    win.refresh()

    while True:
        key = win.getch()
        if key in (ord('y'), ord('Y')):
            return True
        if key in (ord('n'), ord('N'), 27):
            return False

