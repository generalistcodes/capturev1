from __future__ import annotations

import os
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

