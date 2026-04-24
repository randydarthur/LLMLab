# tui/widgets/listbox.py

import curses
from ollama_lab.tui.safe_curses import safe_addstr


def choice_popup(stdscr, title, prompt, choices):
    """
    Centered popup to choose one item from a list.

    Returns the selected choice (string) or None if cancelled.
    Navigation:
      - Up/Down arrows to move
      - Enter to select
      - ESC to cancel
    """
    if not choices:
        return None

    h, w = stdscr.getmaxyx()

    max_choice_len = max(len(c) for c in choices)
    box_width = max(len(title), len(prompt), max_choice_len + 4, 40) + 4
    max_visible_choices = min(len(choices), 10)
    box_height = 6 + max_visible_choices

    start_y = max(0, (h - box_height) // 2)
    start_x = max(0, (w - box_width) // 2)

    stdscr.nodelay(False)
    curses.curs_set(0)

    selected_idx = 0
    scroll_offset = 0

    while True:
        stdscr.clear()

        # Draw border
        for y in range(box_height):
            for x in range(box_width):
                if y in (0, box_height - 1) or x in (0, box_width - 1):
                    safe_addstr(stdscr, start_y + y, start_x + x, "#")

        # Title
        safe_addstr(stdscr, start_y + 1, start_x + 2, title[: box_width - 4])

        # Prompt
        safe_addstr(stdscr, start_y + 2, start_x + 2, prompt[: box_width - 4])

        # Choices window
        list_top = start_y + 3
        list_bottom = start_y + box_height - 3
        visible_height = list_bottom - list_top + 1

        # Adjust scroll
        if selected_idx < scroll_offset:
            scroll_offset = selected_idx
        elif selected_idx >= scroll_offset + visible_height:
            scroll_offset = selected_idx - visible_height + 1

        visible_choices = choices[scroll_offset: scroll_offset + visible_height]

        for i, choice in enumerate(visible_choices):
            y = list_top + i
            prefix = "> " if (scroll_offset + i) == selected_idx else "  "
            line = f"{prefix}{choice}"
            safe_addstr(stdscr, y, start_x + 2, line[: box_width - 4])

        # Footer
        footer = "↑/↓ to move, Enter to select, ESC to cancel"
        safe_addstr(
            stdscr,
            start_y + box_height - 2,
            start_x + 2,
            footer[: box_width - 4],
        )

        stdscr.refresh()
        ch = stdscr.getch()

        if ch == 27:  # ESC
            stdscr.nodelay(True)
            return None

        if ch in (curses.KEY_UP, ord("k")):
            if selected_idx > 0:
                selected_idx -= 1
            continue

        if ch in (curses.KEY_DOWN, ord("j")):
            if selected_idx < len(choices) - 1:
                selected_idx += 1
            continue

        if ch in (10, 13):  # Enter
            stdscr.nodelay(True)
            return choices[selected_idx]

