import os
import platform
import shutil
import subprocess


def launch_terminal_tail(log_path: str):
    """
    Launches a new terminal window that runs `tail -f <log_path>` (or the
    Windows equivalent). This function is non-blocking and returns immediately.

    Supports macOS, Linux, and Windows.
    """

    system = platform.system()
    log_path = os.path.expanduser(log_path)

    # macOS ------------------------------------------------------------------
    if system == "Darwin":
        # AppleScript is the most reliable way to open Terminal and run a command.
        script = f'''
            tell application "Terminal"
                do script "tail -f {log_path}"
                activate
            end tell
        '''
        subprocess.Popen(["osascript", "-e", script])
        return

    # Linux ------------------------------------------------------------------
    if system == "Linux":
        # Try Debian/Ubuntu standard first
        if shutil.which("x-terminal-emulator"):
            subprocess.Popen(["x-terminal-emulator", "-e", f"tail -f {log_path}"])
            return

        # GNOME Terminal
        if shutil.which("gnome-terminal"):
            subprocess.Popen(["gnome-terminal", "--", "tail", "-f", log_path])
            return

        # KDE Konsole
        if shutil.which("konsole"):
            subprocess.Popen(["konsole", "-e", f"tail -f {log_path}"])
            return

        # XFCE Terminal
        if shutil.which("xfce4-terminal"):
            subprocess.Popen(["xfce4-terminal", "-e", f"tail -f {log_path}"])
            return

        # Fallback to xterm
        if shutil.which("xterm"):
            subprocess.Popen(["xterm", "-e", f"tail -f {log_path}"])
            return

        raise RuntimeError("No compatible terminal emulator found on Linux.")

    # Windows ----------------------------------------------------------------
    if system == "Windows":
        # PowerShell equivalent of tail -f
        cmd = f"Get-Content -Path '{log_path}' -Wait"
        subprocess.Popen(
            ["powershell", "-NoExit", "-Command", cmd],
            shell=True
        )
        return

    # Unsupported OS ---------------------------------------------------------
    raise RuntimeError(f"Unsupported OS: {system}")

