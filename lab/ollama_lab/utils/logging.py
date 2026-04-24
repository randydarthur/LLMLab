from datetime import datetime
import os
import threading

# Thread-safe log file writes
_log_lock = threading.Lock()

# Correct log file location (matches registry + log viewer)
LOG_PATH = os.path.expanduser("~/.llmlab/llmlab.log")


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp}[{level}] {msg}"

    # Ensure directory exists
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    # Always write to file
    with _log_lock:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")

    # Only print to stdout if not in curses mode
    if not os.environ.get("LLMLAB_TUI_ACTIVE"):
        print(line)


def read_log_tail(lines: int = 40):
    """
    Return the last N lines of the log file.
    """
    try:
        with open(LOG_PATH, "r") as f:
            return f.readlines()[-lines:]
    except Exception:
        return ["<no log data>"]

