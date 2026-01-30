from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class DriverStatus:
    pidfile: Path
    pid: Optional[int]
    running: bool
    stale_pidfile: bool


def process_exists(pid: int) -> bool:
    """
    Best-effort "is this PID alive?" check.
    - On POSIX: os.kill(pid, 0) is the standard check.
    - On Windows: os.kill exists but semantics differ; this is still a reasonable best-effort.
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it.
        return True
    except OSError:
        return False
    else:
        return True


def read_pidfile(pidfile: Path) -> Optional[int]:
    if not pidfile.exists():
        return None
    text = pidfile.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text.splitlines()[0].strip())
    except ValueError:
        return None


def write_pidfile(pidfile: Path, pid: int) -> None:
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(f"{pid}\n", encoding="utf-8")


def check_status(
    pidfile: Path, *, pid_exists: Callable[[int], bool] = process_exists
) -> DriverStatus:
    pid = read_pidfile(pidfile)
    if pid is None:
        return DriverStatus(pidfile=pidfile, pid=None, running=False, stale_pidfile=False)
    alive = pid_exists(pid)
    return DriverStatus(pidfile=pidfile, pid=pid, running=alive, stale_pidfile=(not alive))


def stop_pid(
    pid: int,
    *,
    timeout_seconds: float = 5.0,
    force: bool = False,
    pid_exists: Callable[[int], bool] = process_exists,
    kill_func: Callable[[int, int], None] = os.kill,
) -> bool:
    """
    Attempt to stop a process:
    - Send SIGTERM, wait up to timeout_seconds.
    - If still alive and force=True, send SIGKILL and wait briefly.
    Returns True if process is not running at the end.
    """
    if pid <= 0:
        return True
    if not pid_exists(pid):
        return True

    kill_func(pid, signal.SIGTERM)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not pid_exists(pid):
            return True
        time.sleep(0.1)

    if not force:
        return not pid_exists(pid)

    try:
        kill_func(pid, signal.SIGKILL)
    except Exception:
        pass
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if not pid_exists(pid):
            return True
        time.sleep(0.1)
    return not pid_exists(pid)

