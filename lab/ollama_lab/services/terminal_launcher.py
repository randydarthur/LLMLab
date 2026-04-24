"""
Unified terminal launcher for LLMLab.

This module launches OS-native terminals running backend-native commands:

  • Interactive model session:  ollama run <repo:variant>
  • Log viewer:                tail -f ~/.llmlab/llmlab.log

This keeps LLMLab fully backend-agnostic and removes all REPL dependencies.
"""

from __future__ import annotations

import os
import sys
import subprocess
from ollama_lab.utils.logging import log


# ------------------------------------------------------------
# Internal helper — launch a new terminal window running a command
# ------------------------------------------------------------

def _launch_new_terminal(command: str, label: str):
    """
    Launch a new OS-native terminal window running the given command.
    `command` must be a full shell command string.
    `label` is used for logging.
    """
    platform = sys.platform

    try:
        # macOS — Terminal.app
        if platform.startswith("darwin"):
            osa_cmd = [
                "osascript",
                "-e",
                f'tell application "Terminal" to do script {command!r}'
            ]
            subprocess.Popen(osa_cmd)
            log(f"[TerminalLauncher] Spawned macOS Terminal for {label}", "INFO")
            return

        # Linux — GNOME Terminal (fallback to xterm)
        elif platform.startswith("linux"):
            try:
                subprocess.Popen(["gnome-terminal", "--", "bash", "-c", command])
                log(f"[TerminalLauncher] Spawned GNOME Terminal for {label}", "INFO")
                return
            except FileNotFoundError:
                pass

            try:
                subprocess.Popen(["xterm", "-e", command])
                log(f"[TerminalLauncher] Spawned xterm for {label}", "INFO")
                return
            except FileNotFoundError:
                pass

            raise RuntimeError("No supported terminal emulator found (gnome-terminal or xterm).")

        # Windows — PowerShell
        elif platform.startswith("win"):
            ps_cmd = [
                "powershell",
                "-NoExit",
                "-Command",
                command
            ]
            subprocess.Popen(ps_cmd)
            log(f"[TerminalLauncher] Spawned PowerShell for {label}", "INFO")
            return

        else:
            raise RuntimeError(f"Unsupported platform for terminal launch: {platform}")

    except Exception as e:
        log(f"[TerminalLauncher] Failed to launch terminal for {label}: {e}", "ERROR")
        raise


# ------------------------------------------------------------
# Interactive model session (T key)
# ------------------------------------------------------------

def launch_interactive_terminal(repo: str, variant: str):
    """
    Launch a new OS-native terminal window running:
        ollama run <repo:variant>
    """
    full_tag = f"{repo}:{variant}"
    cmd = f"ollama run {full_tag}; echo 'Interactive Ollama Session Ended'; exit"

    _launch_new_terminal(cmd, f"interactive session for '{full_tag}'")


# ------------------------------------------------------------
# Log viewer (L key)
# ------------------------------------------------------------

def launch_log_viewer():
    """
    Launch a new OS-native terminal window running:
        tail -f ~/.llmlab/llmlab.log
    """
    log_path = os.path.expanduser("~/.llmlab/llmlab.log")
    cmd = f"tail -f {log_path}; echo 'Control-C to exit'; exit"

    _launch_new_terminal(cmd, "Log viewer launched")

