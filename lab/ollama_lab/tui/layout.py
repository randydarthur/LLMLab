import time
from ollama_lab.utils.metrics import get_cpu_load, get_gpu_load
from ollama_lab.utils.config import MAX_ACTIVE_MODELS
from ollama_lab.utils.errors import ERROR_BANNER, ERROR_BANNER_TIME
from ollama_lab.tui.safe_curses import safe_addstr, CYAN, RED
from ollama_lab.model_intelligence import get_hardware_profile


def draw_header(stdscr, active_count):
    h, w = stdscr.getmaxyx()

    safe_addstr(stdscr, 0, 0, "=== OLLAMA LAB DASHBOARD ===", CYAN)
    safe_addstr(stdscr, 0, max(0, w - 12), time.strftime("%H:%M:%S"))

    hw = get_hardware_profile()
    cpu = get_cpu_load()
    gpu = get_gpu_load()

    backend = hw.get("backend") or "UNKNOWN"
    vram = hw.get("gpu_vram_gb") or "?"

    safe_addstr(
        stdscr,
        1,
        0,
        f"Active Models: {active_count}/{MAX_ACTIVE_MODELS}  Backend: {backend}  VRAM: {vram}GB",
    )

    cpu_display = f"{cpu:.0f}%" if cpu is not None else "N/A"
    gpu_display = f"{gpu:.0f}%" if gpu is not None else "N/A"

    safe_addstr(stdscr, 2, 0, f"CPU Load: {cpu_display}   GPU Load: {gpu_display}")


def draw_error_banner(stdscr):
    if ERROR_BANNER and time.time() - ERROR_BANNER_TIME < 4:
        safe_addstr(stdscr, 3, 0, f"ERROR: {ERROR_BANNER}", RED)


def draw_footer(stdscr):
    h, w = stdscr.getmaxyx()
    safe_addstr(stdscr, h - 1, 0, "q=Quit  a=Add Model  d=Details  l=Logs")

