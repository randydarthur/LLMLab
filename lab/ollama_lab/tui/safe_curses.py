# tui/safe_curses.py

"""
Safe wrappers around curses drawing operations.

This module ensures:
  • No curses.error exceptions bubble up
  • All drawing is clipped to screen bounds
  • Color initialization is optional and safe
"""

import curses


# ------------------------------------------------------------
# Color constants (default to no color)
# ------------------------------------------------------------

CYAN = 0
RED = 0
GREEN = 0
YELLOW = 0


# ------------------------------------------------------------
# Color initialization
# ------------------------------------------------------------

def init_colors():
    """
    Initialize color pairs safely.
    If the terminal does not support colors, all values remain 0.
    """
    global CYAN, RED, GREEN, YELLOW

    try:
        if not curses.has_colors():
            return

        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)

        CYAN = curses.color_pair(1)
        RED = curses.color_pair(2)
        GREEN = curses.color_pair(3)
        YELLOW = curses.color_pair(4)

    except Exception:
        # Terminal without color support or initialization failure
        CYAN = RED = GREEN = YELLOW = 0


# ------------------------------------------------------------
# Safe drawing helpers
# ------------------------------------------------------------

def safe_addstr(stdscr, row, col, text, attr=0):
    """
    Safely draw a string at (row, col), clipped to screen width.
    Never raises curses.error.
    """
    try:
        h, w = stdscr.getmaxyx()

        # Out of bounds row
        if row < 0 or row >= h:
            return

        # Clip column
        if col < 0 or col >= w:
            return

        # Clip text to available width
        max_len = max(0, w - col - 1)
        clipped = text[:max_len]

        stdscr.addstr(row, col, clipped, attr)

    except curses.error:
        # Ignore drawing errors (e.g., writing to last column)
        pass


def safe_addch(stdscr, row, col, ch, attr=0):
    """
    Safely draw a single character at (row, col).
    Useful for borders and box drawing.
    """
    try:
        h, w = stdscr.getmaxyx()

        if row < 0 or row >= h:
            return
        if col < 0 or col >= w:
            return

        stdscr.addch(row, col, ch, attr)

    except curses.error:
        pass

