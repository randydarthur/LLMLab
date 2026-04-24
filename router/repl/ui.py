import curses
import asyncio
import time


class ReplUI:
    def __init__(self, loop):
        self._loop = loop  # MAIN EVENT LOOP

        self._chat_lines = []
        self._json_lines = []
        self._assistant_buffer = ""
        self._exit = False

        # scrollback
        self._chat_scroll = 0
        self._json_scroll = 0

        # model picker
        self.models = []
        self._picker_future = None

        # status bar fields
        self._status_model = None
        self._status_backend = None
        self._status_session = None
        self._status_latency = None
        self._status_tps = None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def add_chat_line(self, line: str):
        self._chat_lines.append(line)

    def append_assistant_token(self, token: str):
        if not self._assistant_buffer:
            self._assistant_buffer = "Assistant: "
            self._chat_lines.append(self._assistant_buffer)
        self._assistant_buffer += token
        self._chat_lines[-1] = self._assistant_buffer

    def finish_assistant_line(self):
        self._assistant_buffer = ""

    def add_json_entry(self, text: str):
        for line in text.splitlines():
            self._json_lines.append(line)

    def request_exit(self):
        self._exit = True

    def set_models(self, models):
        self.models = list(models)

    def set_status(self, model, backend, session_id, latency=None, tps=None):
        self._status_model = model
        self._status_backend = backend
        self._status_session = session_id
        self._status_latency = latency
        self._status_tps = tps

    async def request_model_picker(self):
        """REPL awaits this. UI resolves it when picker returns."""
        self._picker_future = self._loop.create_future()
        return await self._picker_future

    async def run(self, handle_command, handle_message):
        await self._loop.run_in_executor(
            None, curses.wrapper, self._curses_main, handle_command, handle_message
        )

    # ------------------------------------------------------------
    # Internal curses UI
    # ------------------------------------------------------------
    def _curses_main(self, stdscr, handle_command, handle_message):
        curses.curs_set(1)
        stdscr.nodelay(True)
        stdscr.keypad(True)

        input_buf = ""

        while not self._exit:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()

            chat_h = max_y // 2
            input_h = 4
            json_h = max_y - chat_h - input_h - 3
            if json_h < 3:
                json_h = 3

            # -------------------------------
            # Chat window
            # -------------------------------
            chat_win = stdscr.derwin(chat_h, max_x, 0, 0)
            chat_win.box()
            chat_win.addstr(0, 2, " Chat (PgUp/PgDn) ")

            visible_height = chat_h - 2
            max_scroll = max(0, len(self._chat_lines) - visible_height)
            self._chat_scroll = max(0, min(self._chat_scroll, max_scroll))

            start = max(0, len(self._chat_lines) - visible_height - self._chat_scroll)
            end = start + visible_height
            visible_chat = self._chat_lines[start:end]

            for i, line in enumerate(visible_chat):
                chat_win.addnstr(i + 1, 1, line, max_x - 2)

            # -------------------------------
            # Input window
            # -------------------------------
            input_y = chat_h
            input_win = stdscr.derwin(input_h, max_x, input_y, 0)
            input_win.box()
            input_win.addstr(0, 2, " Input ")

            prefix = "Input: "
            text = prefix + input_buf
            for i in range(input_h - 1):
                start_idx = i * (max_x - 2)
                chunk = text[start_idx:start_idx + (max_x - 2)]
                if not chunk:
                    break
                input_win.addnstr(i + 1, 1, chunk, max_x - 2)

            # -------------------------------
            # JSON log window
            # -------------------------------
            json_y = chat_h + input_h
            json_win = stdscr.derwin(json_h, max_x, json_y, 0)
            json_win.box()
            json_win.addstr(0, 2, " JSON Log ([ ] scroll) ")

            json_visible_height = json_h - 2
            json_max_scroll = max(0, len(self._json_lines) - json_visible_height)
            self._json_scroll = max(0, min(self._json_scroll, json_max_scroll))

            jstart = max(0, len(self._json_lines) - json_visible_height - self._json_scroll)
            jend = jstart + json_visible_height
            visible_json = self._json_lines[jstart:jend]

            for i, line in enumerate(visible_json):
                json_win.addnstr(i + 1, 1, line, max_x - 2)

            # -------------------------------
            # Status bar
            # -------------------------------
            status_y = chat_h + input_h + json_h
            status_win = stdscr.derwin(1, max_x, status_y, 0)

            model = self._status_model or "none"
            backend = self._status_backend or "none"
            session_id = self._status_session or "none"

            if self._status_tps is None:
                tps_str = "none"
            else:
                tps = self._status_tps
                if tps < 10:
                    tps_str = f"{tps:.2f}"
                elif tps < 100:
                    tps_str = f"{tps:.1f}"
                else:
                    tps_str = f"{int(tps)}"

            latency_str = f"{self._status_latency}ms" if self._status_latency else "none"

            status_text = (
                f" Model: {model}   Backend: {backend}   "
                f"Session: {session_id}   Lat:{latency_str}   TPS:{tps_str} "
            )

            x = max(0, (max_x - len(status_text)) // 2)

            status_win.attron(curses.A_REVERSE)
            if self._status_model is None or self._status_backend is None:
                status_win.attron(curses.A_DIM)
            status_win.addnstr(0, x, status_text, max_x - x)
            status_win.attroff(curses.A_REVERSE)
            status_win.attroff(curses.A_DIM)

            stdscr.refresh()

            # -------------------------------
            # Input handling
            # -------------------------------
            ch = stdscr.getch()

            if ch == -1:
                time.sleep(0.01)
                continue

            if ch in (curses.KEY_ENTER, 10, 13):
                text = input_buf.strip()
                input_buf = ""
                if not text:
                    continue

                if text.startswith("/"):
                    self._loop.call_soon_threadsafe(
                        asyncio.create_task, handle_command(text)
                    )
                else:
                    self._loop.call_soon_threadsafe(
                        asyncio.create_task, handle_message(text)
                    )

            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                input_buf = input_buf[:-1]

            elif ch == 3:
                self._exit = True

            elif ch == curses.KEY_PPAGE:
                self._chat_scroll += 1
            elif ch == curses.KEY_NPAGE:
                self._chat_scroll -= 1

            elif ch == ord('['):
                self._json_scroll += 1
            elif ch == ord(']'):
                self._json_scroll -= 1

            elif ch == curses.KEY_F2 and self.models:
                chosen = self._model_picker(stdscr)
                if self._picker_future and not self._picker_future.done():
                    self._picker_future.set_result(chosen)

            elif 32 <= ch <= 126:
                input_buf += chr(ch)

    # ------------------------------------------------------------
    # Model picker
    # ------------------------------------------------------------
    def _model_picker(self, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        if not self.models:
            return None

        h = min(len(self.models) + 4, max_y - 4)
        w = min(max(len(m) for m in self.models) + 6, max_x - 4)
        y = (max_y - h) // 2
        x = (max_x - w) // 2

        win = stdscr.derwin(h, w, y, x)
        win.keypad(True)
        curses.curs_set(0)

        idx = 0
        while True:
            win.clear()
            win.box()
            win.addstr(0, 2, " Select Model (F2/Esc to cancel) ")

            visible = self.models
            max_items = h - 2
            start = max(0, min(idx - max_items // 2, len(visible) - max_items))
            start = max(0, start)
            end = min(len(visible), start + max_items)

            for i, m in enumerate(visible[start:end]):
                row = i + 1
                if start + i == idx:
                    win.attron(curses.A_REVERSE)
                    win.addnstr(row, 2, m, w - 4)
                    win.attroff(curses.A_REVERSE)
                else:
                    win.addnstr(row, 2, m, w - 4)

            win.refresh()
            ch = win.getch()

            if ch in (curses.KEY_UP, ord('k')):
                idx = (idx - 1) % len(self.models)
            elif ch in (curses.KEY_DOWN, ord('j')):
                idx = (idx + 1) % len(self.models)
            elif ch in (curses.KEY_ENTER, 10, 13):
                curses.curs_set(1)
                return self.models[idx]
            elif ch in (curses.KEY_F2, 27):
                curses.curs_set(1)
                return None

