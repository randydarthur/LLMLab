# log_repl.py

import time
import os
from ollama_lab.utils.logging import LOG_PATH
from ollama_lab.services.registry import get_settings


def main():
    settings = get_settings()
    max_lines = getattr(settings, "log_history_lines", 1000)

    print(f"LLMLab Log Viewer — last {max_lines} lines")
    print("Press Ctrl-C to exit.")
    print("-" * 60)

    buffer = []
    last_size = 0

    # Wait for log file to exist
    while not os.path.exists(LOG_PATH):
        print(f"Waiting for log file: {LOG_PATH}")
        time.sleep(0.5)

    with open(LOG_PATH, "r") as f:
        f.seek(0, 2)

        while True:
            # Detect truncation
            current_size = os.path.getsize(LOG_PATH)
            if current_size < last_size:
                f.seek(0)
                buffer = []
            last_size = current_size

            lines = f.readlines()
            if not lines:
                time.sleep(0.2)
                continue

            for line in lines:
                buffer.append(line.rstrip("\n"))
                if len(buffer) > max_lines:
                    buffer = buffer[-max_lines:]

            # Redraw
            print("\033[2J\033[H", end="")
            print(f"LLMLab Log Viewer — last {max_lines} lines")
            print("-" * 60)

            for ln in buffer:
                print(ln)

            print("-" * 60)
            print("Ctrl-C to exit.")

