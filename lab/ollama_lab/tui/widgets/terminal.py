# tui/widgets/terminal.py

import curses
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

from ollama_lab.tui.safe_curses import safe_addstr
from ollama_lab.services.registry import get_settings


# ------------------------------------------------------------
# Bind IP helper
# ------------------------------------------------------------

def _get_bind_ip() -> str:
    """
    Resolve global bind_ip from registry settings.
    Fallback to 127.0.0.1 if missing.
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
# Color initialization
# ------------------------------------------------------------

def _init_terminal_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)    # input
    curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)   # output
    curses.init_pair(7, curses.COLOR_RED, curses.COLOR_BLACK)     # error
    curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # header


# ------------------------------------------------------------
# Interactive terminal popup for a model
# ------------------------------------------------------------

def terminal_popup(stdscr, service_name, port):
    """
    Scrollable REPL:
      • Header at top
      • Scrollable history above prompt
      • Prompt fixed at bottom
      • Arrow keys scroll history
      • Input in CYAN, output in GREEN, errors in RED, header in YELLOW
      • Timestamped responses
      • Prompt: model-name(port)>
      • Empty line exits
    """
    _init_terminal_colors()
    curses.curs_set(1)

    bind_ip = _get_bind_ip()
    h, w = stdscr.getmaxyx()
    stdscr.clear()

    header = f"=== TERMINAL: {service_name}({bind_ip}:{port}) ==="
    prompt_prefix = f"{service_name}({port})> "

    history = []  # list of (kind, text)
    scroll_offset = 0  # 0 = bottom

    def redraw():
        stdscr.clear()

        # Header
        if curses.has_colors():
            stdscr.addstr(0, 0, header[: w - 1], curses.color_pair(8))
        else:
            safe_addstr(stdscr, 0, 0, header[: w - 1])

        # History window: lines 1 .. h-3
        hist_top = 1
        hist_bottom = h - 2
        hist_height = max(0, hist_bottom - hist_top + 1)

        # Determine visible slice
        if history:
            start = max(0, len(history) - hist_height - scroll_offset)
            end = start + hist_height
            visible = history[start:end]
        else:
            visible = []

        # Render visible lines
        y = hist_top
        for kind, text in visible:
            if y > hist_bottom:
                break
            color = 0
            if curses.has_colors():
                if kind == "input":
                    color = curses.color_pair(5)
                elif kind == "output":
                    color = curses.color_pair(6)
                elif kind == "error":
                    color = curses.color_pair(7)

            if color:
                stdscr.addstr(y, 0, text[: w - 1], color)
            else:
                safe_addstr(stdscr, y, 0, text[: w - 1])
            y += 1

        # Prompt line
        stdscr.move(h - 1, 0)
        stdscr.clrtoeol()
        if curses.has_colors():
            stdscr.addstr(h - 1, 0, prompt_prefix, curses.color_pair(5))
        else:
            safe_addstr(stdscr, h - 1, 0, prompt_prefix)

        stdscr.refresh()

    input_buffer = ""
    stdscr.nodelay(False)

    while True:
        redraw()
        stdscr.move(h - 1, len(prompt_prefix) + len(input_buffer))
        ch = stdscr.getch()

        # Scrolling
        if ch in (curses.KEY_UP, curses.KEY_PPAGE):
            if len(history) > 0:
                scroll_offset = min(len(history) - 1, scroll_offset + 1)
            continue

        if ch in (curses.KEY_DOWN, curses.KEY_NPAGE):
            scroll_offset = max(0, scroll_offset - 1)
            continue

        if ch == curses.KEY_HOME:
            scroll_offset = len(history)
            continue

        if ch == curses.KEY_END:
            scroll_offset = 0
            continue

        # Backspace
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if input_buffer:
                input_buffer = input_buffer[:-1]
            continue

        # Enter
        if ch in (10, 13):
            prompt = input_buffer.strip()
            if prompt == "":
                break  # empty line exits

            # Record input
            history.append(("input", prompt_prefix + prompt))
            scroll_offset = 0
            input_buffer = ""
            redraw()

            # Send to model
            try:
                url = f"http://{bind_ip}:{port}/api/generate"
                r = requests.post(
                    url,
                    json={"prompt": prompt},
                    timeout=60,
                )
                r.raise_for_status()
                data = r.json()
                resp = data.get("response", "")
                ts = datetime.now().strftime("%H:%M:%S")
                lines = resp.splitlines() or ["<no response>"]
                for line in lines:
                    history.append(("output", f"[{ts}] {line}"))
            except Exception as e:
                ts = datetime.now().strftime("%H:%M:%S")
                history.append(("error", f"[{ts}] ERROR: {e}"))

            scroll_offset = 0
            continue

        # ESC exits
        if ch == 27:
            break

        # Printable ASCII
        if 32 <= ch <= 126:
            input_buffer += chr(ch)
            continue

    curses.curs_set(0)
    stdscr.nodelay(True)

