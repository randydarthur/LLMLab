import curses
import socket
import time

psutil = None
try:
    import psutil
except ImportError:
    pass

from ollama_lab.tui.safe_curses import safe_addstr
from ollama_lab.utils.logging import LOG_PATH
from ollama_lab.services.registry import get_settings
from ollama_lab.services.llm_backend_factory import get_llm_backend
from ollama_lab.tui.widgets import modal_message


# ------------------------------------------------------------
# System status (CPU / RAM / GPU)
# ------------------------------------------------------------

def get_system_status():
    """
    Return (CPU%, RAM%, GPU%) or "N/A" if unavailable.
    """
    if psutil is None:
        return ("N/A", "N/A", "N/A")

    try:
        cpu = psutil.cpu_percent(interval=None)
    except Exception:
        cpu = "N/A"

    try:
        ram = psutil.virtual_memory().percent
    except Exception:
        ram = "N/A"

    gpu = "N/A"  # placeholder for future GPU integration
    return cpu, ram, gpu


def _get_bind_ip() -> str:
    """
    Return the configured bind_ip or fallback to 127.0.0.1.
    """
    try:
        settings = get_settings() or {}
        bind_ip = settings.get("bind_ip")
        if isinstance(bind_ip, str) and bind_ip.strip():
            return bind_ip.strip()
    except Exception:
        pass
    return "127.0.0.1"


# ------------------------------------------------------------
# Catalog Refresh Progress Modal
# ------------------------------------------------------------

def show_catalog_refresh_modal(stdscr):
    """
    Animated spinner modal shown during catalog refresh.
    """
    h, w = stdscr.getmaxyx()
    box_w = 44
    box_h = 9

    start_y = max(0, (h - box_h) // 2)
    start_x = max(0, (w - box_w) // 2)

    stdscr.nodelay(True)
    curses.curs_set(0)

    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0

    while True:
        stdscr.clear()

        # Border
        for y in range(box_h):
            for x in range(box_w):
                if y in (0, box_h - 1) or x in (0, box_w - 1):
                    safe_addstr(stdscr, start_y + y, start_x + x, "#")

        safe_addstr(stdscr, start_y + 2, start_x + 2, "Refreshing Catalog...")
        safe_addstr(stdscr, start_y + 4, start_x + 2, f"Please wait {spinner[idx]}")

        stdscr.refresh()
        idx = (idx + 1) % len(spinner)

        ch = stdscr.getch()
        if ch == ord("\n"):
            break

        time.sleep(0.1)

    stdscr.nodelay(True)


# ------------------------------------------------------------
# Main screen
# ------------------------------------------------------------

def draw_main_screen(stdscr, models, selected, catalog_ts=None):
    """
    Draw the main LLMLab TUI screen.
    """
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    backend = get_llm_backend()
    bind_ip = _get_bind_ip()
    daemon_port = 11434

    # ---------------------------------------
    # System Status
    # ---------------------------------------
    cpu, ram, gpu = get_system_status()

    def fmt_pct(val):
        return f"{val:.0f}%" if isinstance(val, (int, float)) else str(val)

    status = f"CPU:{fmt_pct(cpu)}   RAM:{fmt_pct(ram)}   GPU:{gpu}"
    safe_addstr(stdscr, 0, 0, status[: w - 1])

    # ---------------------------------------
    # Ollama Daemon Status
    # ---------------------------------------
    try:
        daemon_running = backend.is_available()
    except Exception:
        daemon_running = False

    daemon_state = "Running" if daemon_running else "Stopped"
    daemon_addr = f"{bind_ip}:{daemon_port}"

    daemon_line = f"Ollama Daemon: {daemon_state:<8}  Address: {daemon_addr}"
    safe_addstr(stdscr, 2, 0, daemon_line[: w - 1])

    # ---------------------------------------
    # Catalog Timestamp
    # ---------------------------------------
    if catalog_ts:
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(catalog_ts))
        cat_line = f"Catalog last refreshed: {ts_str}"
    else:
        cat_line = "Catalog last refreshed: Never"

    safe_addstr(stdscr, 3, 0, cat_line[: w - 1])

    # ---------------------------------------
    # Models Header
    # ---------------------------------------
    safe_addstr(stdscr, 5, 0, "Models:")

    # Layout
    tail_lines = 6
    command_bar_height = 2
    list_top = 6
    list_height = h - list_top - command_bar_height - tail_lines - 1
    if list_height < 1:
        list_height = 1

    model_names = list(models.keys())  # full_tag keys
    total = len(model_names)

    # Scrolling window
    if total <= list_height:
        start_idx = 0
    else:
        start_idx = min(
            max(0, selected - list_height + 1),
            max(0, total - list_height),
        )
    end_idx = min(total, start_idx + list_height)

    # ---------------------------------------
    # Model Rows (full_tag keyed)
    # ---------------------------------------
    for row, idx in enumerate(range(start_idx, end_idx)):
        full_tag = model_names[idx]
        entry = models.get(full_tag, {})

        repo = entry.get("repo", "?")
        variant = entry.get("variant", "?")

        prefix = "> " if idx == selected else "  "
        line = f"{prefix}{full_tag:<30} Repo: {repo:<15} Variant: {variant}"
        safe_addstr(stdscr, list_top + row, 0, line[: w - 1])

    # ---------------------------------------
    # Command Summary
    # ---------------------------------------
    cmd_y = list_top + list_height
    safe_addstr(stdscr, cmd_y, 0, "-" * (w - 1))

    commands = (
        "A:Add  D:Delete  U:Update  P:Repair  V:Verify  "
        "R:Refresh Catalog  S:Start  X:Stop  T:Terminal  L:Logs  H:Help  Q:Quit"
    )

    safe_addstr(stdscr, cmd_y + 1, 0, commands[: w - 1])

    # ---------------------------------------
    # Log Tail
    # ---------------------------------------
    tail_y = cmd_y + 2
    if tail_y < h:
        safe_addstr(stdscr, tail_y, 0, "-" * (w - 1))
        try:
            with open(LOG_PATH, "r") as f:
                log_lines = f.readlines()[-tail_lines:]
        except Exception:
            log_lines = ["<no log file>"]

        for i, line in enumerate(log_lines):
            if tail_y + 1 + i >= h:
                break
            safe_addstr(stdscr, tail_y + 1 + i, 0, line.rstrip()[: w - 1])

    stdscr.refresh()


# ------------------------------------------------------------
# Help screen
# ------------------------------------------------------------

def draw_help_screen(stdscr):
    h, w = stdscr.getmaxyx()

    help_lines = [
        "LLMLab Help",
        "",
        "A — Add Model",
        "D — Delete Model",
        "U — Update Model",
        "P — Repair Model",
        "V — Verify Integrity",
        "R — Refresh Catalog",
        "S — Start Ollama Daemon",
        "X — Stop Ollama Daemon",
        "T — Interactive Terminal",
        "L — View Logs",
        "H — Help",
        "Q — Quit",
        "",
        "Press any key to return...",
    ]

    box_width = max(len(line) for line in help_lines) + 4
    box_height = len(help_lines) + 2
    start_y = max(0, (h - box_height) // 2)
    start_x = max(0, (w - box_width) // 2)

    stdscr.nodelay(False)
    stdscr.clear()

    for i, line in enumerate(help_lines):
        safe_addstr(stdscr, start_y + i, start_x, line[: box_width - 2])

    stdscr.refresh()
    stdscr.getch()
    stdscr.nodelay(True)


# ------------------------------------------------------------
# Log viewer
# ------------------------------------------------------------

def draw_log_viewer(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(False)

    h, w = stdscr.getmaxyx()

    try:
        with open(LOG_PATH, "r") as f:
            lines = [ln.rstrip("\n") for ln in f.readlines()]
    except Exception:
        lines = ["<no log file>"]

    total = len(lines)
    scroll = 0
    view_height = h - 2

    def redraw():
        stdscr.clear()
        header = f"Log Viewer — {LOG_PATH}  (ESC/q to exit)"
        safe_addstr(stdscr, 0, 0, header[: w - 1])

        start = max(0, total - view_height - scroll)
        end = start + view_height
        visible = lines[start:end]

        for i, line in enumerate(visible):
            safe_addstr(stdscr, 1 + i, 0, line[: w - 1])

        footer = f"Lines {start+1}-{min(end,total)} of {total}"
        safe_addstr(stdscr, h - 1, 0, footer[: w - 1])
        stdscr.refresh()

    redraw()

    while True:
        ch = stdscr.getch()

        if ch in (27, ord("q"), ord("Q")):
            break

        if ch == curses.KEY_UP:
            if scroll < total - 1:
                scroll += 1
                redraw()
        elif ch == curses.KEY_DOWN:
            if scroll > 0:
                scroll -= 1
                redraw()
        elif ch == curses.KEY_PPAGE:
            scroll = min(total - 1, scroll + view_height)
            redraw()
        elif ch == curses.KEY_NPAGE:
            scroll = max(0, scroll - view_height)
            redraw()
        elif ch == curses.KEY_HOME:
            scroll = total - 1
            redraw()
        elif ch == curses.KEY_END:
            scroll = 0
            redraw()

    stdscr.nodelay(True)

