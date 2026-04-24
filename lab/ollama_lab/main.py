#!/usr/bin/env python3
import curses
import sys
import time
import traceback
import os
import argparse
import ipaddress

from ollama_lab.utils.logging import log

# Lifecycle actions (full_tag only)
from ollama_lab.models.lifecycle import (
    add_model,
    delete_model,
    update_model,
    repair_model,
)
from ollama_lab.models.integrity import verify_model_integrity

# Unified backend
from ollama_lab.services.llm_backend_factory import get_llm_backend

# Terminal launchers
from ollama_lab.services.terminal_launcher import (
    launch_interactive_terminal,
    launch_log_viewer,
)

# Registry helpers
from ollama_lab.services.registry import (
    get_settings,
    set_settings,
    get_log_history_lines,
    set_log_history_lines,
    DEFAULT_LOG_HISTORY_LINES,
    get_catalog_last_refreshed,
    set_catalog_last_refreshed,
    list_installed,
    rebuild_registry_from_backend,
)

# Catalog helpers
from ollama_lab.services.model_catalog import (
    is_catalog_empty,
    refresh_catalog,
)

from ollama_lab.tui.widgets import terminal_popup, modal_message
from ollama_lab.tui.screens import draw_main_screen, draw_help_screen
from ollama_lab.tui.safe_curses import init_colors


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _validate_ip(ip_str: str) -> bool:
    try:
        ipaddress.ip_address(ip_str)
        return True
    except Exception:
        return False


def _apply_bind_ip_override(ip_str: str):
    if not _validate_ip(ip_str):
        print(f"ERROR: Invalid IP address '{ip_str}'")
        sys.exit(1)

    settings = get_settings()
    settings["bind_ip"] = ip_str
    set_settings(settings)
    print(f"Bind IP set to {ip_str}")


def _wrap(stdscr, fn, *args, **kwargs):
    try:
        return fn(stdscr, *args, **kwargs)
    except Exception as e:
        curses.endwin()
        log(f"[FATAL] Unhandled exception: {e}", "ERROR")
        traceback.print_exc()
        sys.exit(1)


def _handle_add_model(stdscr):
    from ollama_lab.tui.widgets import text_input_popup

    repo = text_input_popup(
        stdscr,
        "ADD MODEL",
        "Enter Ollama model repo (e.g., llama3, mistral:7b):",
    )
    if not repo:
        return
    add_model(stdscr, repo)


# ------------------------------------------------------------
# Build installed-only model list (full_tag keyed)
# ------------------------------------------------------------

def _build_installed_models():
    installed = list_installed()
    models = {}

    for key, entry in installed.items():
        full_tag = entry.get("full_tag")
        if not full_tag or ":" not in full_tag:
            continue

        repo = entry.get("repo")
        variant = entry.get("variant")

        models[full_tag] = {
            "full_tag": full_tag,
            "repo": repo,
            "variant": variant,
        }

    return dict(sorted(models.items(), key=lambda kv: kv[0]))


# ------------------------------------------------------------
# Main TUI loop
# ------------------------------------------------------------

def main(stdscr):
    curses.curs_set(0)
    init_colors()
    stdscr.nodelay(True)
    stdscr.timeout(300)

    backend = get_llm_backend()
    selected = 0

    # ------------------------------------------------------------
    # Sync registry with backend on startup
    # ------------------------------------------------------------
    try:
        rebuild_registry_from_backend(backend)
    except Exception as e:
        modal_message(stdscr, ["Failed to sync installed models:", str(e)])

    # ------------------------------------------------------------
    # Seed catalog if empty
    # ------------------------------------------------------------
    if is_catalog_empty():
        modal_message(stdscr, ["Catalog empty.", "Seeding catalog...", "Please wait."])
        try:
            refresh_catalog()
            set_catalog_last_refreshed(time.time())
            modal_message(stdscr, ["Catalog seeded successfully."])
        except Exception as e:
            modal_message(stdscr, ["Catalog seed failed.", str(e)])

    # ------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------
    while True:

        catalog_ts = get_catalog_last_refreshed()

        # Installed-only model list
        models = _build_installed_models()
        model_names = list(models.keys())

        if selected >= len(model_names):
            selected = max(0, len(model_names) - 1)

        draw_main_screen(stdscr, models, selected, catalog_ts)
        stdscr.refresh()

        key = stdscr.getch()
        if key == -1:
            continue

        # Quit
        if key in (ord("q"), ord("Q")):
            break

        # Navigation
        if key == curses.KEY_UP:
            selected = max(0, selected - 1)
            continue
        if key == curses.KEY_DOWN:
            selected = min(max(0, len(model_names) - 1), selected + 1)
            continue

        # Add Model (catalog modal)
        if key in (ord("a"), ord("A")):
            from ollama_lab.tui.model_catalog_modal import open_model_catalog_modal
            open_model_catalog_modal(stdscr)
            continue

        # Help
        if key in (ord("h"), ord("H")):
            draw_help_screen(stdscr)
            continue

        # Log viewer
        if key in (ord("l"), ord("L")):
            launch_log_viewer()
            continue

        # Refresh Catalog
        if key in (ord("r"), ord("R")):
            modal_message(stdscr, ["Refreshing catalog...", "Please wait."])
            try:
                refresh_catalog()
                set_catalog_last_refreshed(time.time())
                modal_message(stdscr, ["Catalog refreshed successfully."])
            except Exception as e:
                modal_message(stdscr, ["Catalog refresh failed.", str(e)])
            continue

        # No installed models? Skip actions
        if not model_names:
            continue

        full_tag = model_names[selected]
        repo, variant = full_tag.split(":", 1)

        # Delete Model
        if key == ord("D"):
            delete_model(stdscr, full_tag)
            continue

        # Update Model
        if key in (ord("u"), ord("U")):
            update_model(stdscr, full_tag)
            continue

        # Repair Model
        if key in (ord("p"), ord("P")):
            repair_model(stdscr, full_tag)
            continue

        # Verify Integrity
        if key in (ord("v"), ord("V")):
            verify_model_integrity(stdscr, full_tag)
            continue

        # Start daemon
        if key in (ord("s"), ord("S")):
            try:
                backend.start_daemon()
                modal_message(stdscr, ["Ollama daemon started."])
            except Exception as e:
                modal_message(stdscr, ["Failed to start daemon.", str(e)])
            continue

        # Stop daemon
        if key in (ord("x"), ord("X")):
            try:
                backend.stop_daemon()
                modal_message(stdscr, ["Ollama daemon stopped."])
            except Exception as e:
                modal_message(stdscr, ["Failed to stop daemon.", str(e)])
            continue

        # Interactive terminal
        if key in (ord("t"), ord("T")):
            launch_interactive_terminal(repo, variant)
            continue


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="LLMLab TUI")

    parser.add_argument(
        "--bind_ip",
        type=str,
        help="Override and persist the bind IP for all model servers",
    )

    parser.add_argument(
        "--log-history-lines",
        type=int,
        help="Number of log lines to retain in the log viewer",
    )

    args, unknown = parser.parse_known_args()

    if args.bind_ip:
        _apply_bind_ip_override(args.bind_ip)

    if args.log_history_lines:
        set_log_history_lines(args.log_history_lines)
    else:
        current = get_log_history_lines()
        if current is None:
            set_log_history_lines(DEFAULT_LOG_HISTORY_LINES)

    os.environ["LLMLAB_TUI_ACTIVE"] = "1"
    curses.wrapper(main)
    del os.environ["LLMLAB_TUI_ACTIVE"]

