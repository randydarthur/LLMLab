import socket
import platform
from typing import Tuple, Set
psutil = None
try:
    import psutil
except ImportError:
    pass

def _reserved_port_ranges() -> Tuple[Tuple[int, int], ...]:
    """
    OS-specific reserved / noisy ranges we want to avoid.
    Ranges are inclusive: (start, end).
    """
    system = platform.system()

    # Well-known + registered ports: 0–49151
    # Ephemeral defaults:
    #   - Linux:   32768–60999 (often)
    #   - macOS:   49152–65535
    #   - Windows: 49152–65535 (default)
    #
    # We pick a "lab" range that:
    #   - avoids well-known ports
    #   - avoids typical ephemeral ranges
    #   - avoids known noisy system services
    #
    # We'll still probe for actual usage, but this keeps us out of trouble.
    if system == "Darwin":
        # macOS: avoid 0–30000 and 49152–65535
        return (
            (0, 30000),
            (49152, 65535),
        )
    elif system == "Windows":
        # Windows: avoid 0–30000 and 49152–65535
        return (
            (0, 30000),
            (49152, 65535),
        )
    else:
        # Linux and others: avoid 0–30000 and 32768–60999
        return (
            (0, 30000),
            (32768, 60999),
        )


def _lab_port_range() -> Tuple[int, int]:
    """
    Preferred lab range after excluding reserved ranges.
    We choose a mid-band that is usually quiet.
    """
    # We'll use 30001–45000 as our primary band.
    # This is outside typical ephemeral ranges on macOS/Windows
    # and above most well-known ports.
    return 30001, 45000


def _is_in_reserved(port: int, reserved: Tuple[Tuple[int, int], ...]) -> bool:
    for start, end in reserved:
        if start <= port <= end:
            return True
    return False

def _current_listen_ports() -> set[int]:
    """
    Return a set of ports that are currently in LISTEN state.

    On platforms (notably macOS without elevated permissions) where
    psutil.net_connections() may raise AccessDenied, we degrade
    gracefully and return an empty set, relying on bind() to be the
    final arbiter of availability.
    """
    used: set[int] = set()
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        # Can't inspect system connections; fall back to bind-only checks.
        return used
    except Exception:
        # Any unexpected failure: be conservative and just skip psutil data.
        return used

    for c in conns:
        try:
            if c.laddr and c.status == psutil.CONN_LISTEN:
                used.add(c.laddr.port)
        except Exception:
            # Be robust against weird/partial entries
            continue

    return used


def _can_bind(port: int) -> bool:
    """
    Try binding to 127.0.0.1:port to confirm availability.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_next_port(
    start: int = None,
    end: int = None,
    max_probes: int = 2000,
) -> int:
    """
    Hardened, cross-platform port allocator.

    Strategy:
      1. Choose a lab range (default 30001–45000).
      2. Exclude OS-specific reserved/noisy ranges.
      3. Collect currently LISTENing ports via psutil.
      4. Probe ports in the lab range:
         - skip if in reserved range
         - skip if already LISTENing
         - try to bind to confirm availability
      5. If no port found in lab range, fall back to a broader scan.

    Raises:
      RuntimeError if no free port can be found within the probe budget.
    """
    reserved = _reserved_port_ranges()
    if start is None or end is None:
        start, end = _lab_port_range()

    if start >= end:
        raise ValueError(f"Invalid port range: {start}–{end}")

    used_listen = _current_listen_ports()

    probes = 0
    # First pass: preferred lab range
    for port in range(start, end + 1):
        if probes >= max_probes:
            break
        probes += 1

        if _is_in_reserved(port, reserved):
            continue
        if port in used_listen:
            continue
        if _can_bind(port):
            return port

    # Second pass: broader scan above end, but still avoiding reserved ranges
    # We cap at 65535 (max TCP port).
    for port in range(end + 1, 65535 + 1):
        if probes >= max_probes:
            break
        probes += 1

        if _is_in_reserved(port, reserved):
            continue
        if port in used_listen:
            continue
        if _can_bind(port):
            return port

    raise RuntimeError(
        f"No free port available after probing {probes} candidates "
        f"(preferred range {start}–{end}, with reserved ranges {reserved})"
    )

