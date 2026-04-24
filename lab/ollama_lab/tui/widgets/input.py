# tui/widgets/input.py

import curses
from ollama_lab.tui.safe_curses import safe_addstr


def text_input_popup(stdscr, title, prompt):
    """
    Centered text input popup.
    - Title at top
    - Prompt text
    - Input field
    - ESC cancels (returns None)
    - Enter submits (returns string)
    """
    h, w = stdscr.getmaxyx()

    box_width = max(len(title), len(prompt), 40) + 4
    box_height = 8

    start_y = max(0, (h - box_height) // 2)
    start_x = max(0, (w - box_width) // 2)

    stdscr.nodelay(False)
    curses.curs_set(1)

    input_buffer = ""

    while True:
        stdscr.clear()

        # Draw border
        for y in range(box_height):
            for x in range(box_width):
                if y in (0, box_height - 1) or x in (0, box_width - 1):
                    safe_addstr(stdscr, start_y + y, start_x + x, "#")

        # Title
        safe_addstr(stdscr, start_y + 1, start_x + 2, title)

        # Prompt
        safe_addstr(stdscr, start_y + 3, start_x + 2, prompt)

        # Input field
        safe_addstr(stdscr, start_y + 5, start_x + 2, input_buffer)

        stdscr.refresh()
        ch = stdscr.getch()

        # ESC cancels
        if ch == 27:
            curses.curs_set(0)
            stdscr.nodelay(True)
            return None

        # Enter submits
        if ch in (10, 13):
            curses.curs_set(0)
            stdscr.nodelay(True)
            return input_buffer.strip()

        # Backspace
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if input_buffer:
                input_buffer = input_buffer[:-1]
            continue

        # Printable ASCII
        if 32 <= ch <= 126:
            input_buffer += chr(ch)
            continue

