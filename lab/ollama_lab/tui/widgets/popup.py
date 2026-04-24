# tui/widgets/popup.py

import curses
from ollama_lab.tui.safe_curses import safe_addstr


# ------------------------------------------------------------
# Modal message popup
# ------------------------------------------------------------

def modal_message(stdscr, lines):
    """
    Simple centered modal that displays a list of text lines.
    Blocks until any key is pressed.
    """
    h, w = stdscr.getmaxyx()
    box_width = max(len(line) for line in lines) + 4
    box_height = len(lines) + 4

    start_y = max(0, (h - box_height) // 2)
    start_x = max(0, (w - box_width) // 2)

    stdscr.nodelay(False)
    stdscr.clear()

    # Draw border
    for y in range(box_height):
        for x in range(box_width):
            if y in (0, box_height - 1) or x in (0, box_width - 1):
                safe_addstr(stdscr, start_y + y, start_x + x, "#")

    # Draw text
    for i, line in enumerate(lines):
        safe_addstr(stdscr, start_y + 2 + i, start_x + 2, line)

    safe_addstr(stdscr, start_y + box_height - 2, start_x + 2, "Press any key...")
    stdscr.refresh()
    stdscr.getch()
    stdscr.nodelay(True)


# ------------------------------------------------------------
# Delete confirmation popup
# ------------------------------------------------------------

def confirm_delete(stdscr, name):
    """
    Confirmation modal for deleting a model.
    Returns True if user confirms, False otherwise.
    """
    h, w = stdscr.getmaxyx()
    text = f"Delete model '{name}'? (y/n)"
    box_width = len(text) + 4
    box_height = 5

    start_y = max(0, (h - box_height) // 2)
    start_x = max(0, (w - box_width) // 2)

    stdscr.nodelay(False)
    stdscr.clear()

    # Draw box
    for y in range(box_height):
        for x in range(box_width):
            if y in (0, box_height - 1) or x in (0, box_width - 1):
                safe_addstr(stdscr, start_y + y, start_x + x, "#")

    safe_addstr(stdscr, start_y + 2, start_x + 2, text)
    stdscr.refresh()

    while True:
        ch = stdscr.getch()
        if ch in (ord("y"), ord("Y")):
            stdscr.nodelay(True)
            return True
        if ch in (ord("n"), ord("N"), 27):  # ESC also cancels
            stdscr.nodelay(True)
            return False

