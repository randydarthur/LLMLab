"""
Central logging surface for the LLMLab LLM Router.

Enhancements:
- Persistent logging to ~/.llmlab/router.log
- Automatic directory creation
- Bounded in-memory ring buffer (max 10,000 lines)
- Structured timestamped log entries
- Optional JSON mode (future-proof)
- Async-safe writes
"""

from typing import List, Literal, Optional
from datetime import datetime
import asyncio
import json
from pathlib import Path


Severity = Literal["INFO", "WARN", "ERROR", "FATAL"]

Subsystem = Literal[
    "Routing Engine",
    "Session Manager",
    "Task Classifier",
    "Model Registry",
    "Backend Health",
    "Backend Factory",
    "API Layer",
]


class RouterLogger:
    """
    Central bounded logger for router subsystems.
    Exported.
    """

    MAX_LINES = 10_000

    def __init__(self, json_mode: bool = False):
        self._lines: List[str] = []
        self._lock = asyncio.Lock()
        self._json_mode = json_mode

        # Persistent log path
        home = Path.home()
        self._log_dir = home / ".llmlab"
        self._log_file = self._log_dir / "router.log"

        # Ensure directory exists
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Ensure file exists
        if not self._log_file.exists():
            self._log_file.touch()

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    async def log(
        self,
        severity: Severity,
        subsystem: Subsystem,
        message: str,
        extra: Optional[dict] = None,
    ) -> None:
        """
        Append a structured log entry with timestamp, severity, subsystem.
        Exported.
        """
        ts = datetime.now().strftime("%Y-%m-%d:%H:%M:%S.%f")[:-3]

        if self._json_mode:
            entry_obj = {
                "timestamp": ts,
                "severity": severity,
                "subsystem": subsystem,
                "message": message,
                "extra": extra or {},
            }
            entry = json.dumps(entry_obj, ensure_ascii=False)
        else:
            entry = f"{ts} [{severity}] [{subsystem}] {message}"

        async with self._lock:
            # In-memory buffer
            self._lines.append(entry)
            self._prune_if_needed()

            # Persistent append
            self._append_to_file(entry)

    async def get_logs(self) -> List[str]:
        """
        Return a copy of the current in-memory log buffer.
        Exported.
        """
        async with self._lock:
            return list(self._lines)

    async def clear(self) -> None:
        """
        Clear in-memory and persistent logs.
        Exported.
        """
        async with self._lock:
            self._lines.clear()
            self._log_file.write_text("")

    # ------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------

    def _prune_if_needed(self) -> None:
        """
        Ensure log never exceeds MAX_LINES by pruning oldest entries.
        Internal.
        """
        excess = len(self._lines) - self.MAX_LINES
        if excess > 0:
            del self._lines[0:excess]

    def _append_to_file(self, entry: str) -> None:
        """
        Append a single log entry to ~/.llmlab/router.log.
        Internal.
        """
        try:
            with self._log_file.open("a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            # Avoid recursive logging on file errors
            pass

