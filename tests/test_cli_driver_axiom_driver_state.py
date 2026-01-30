from __future__ import annotations

from pathlib import Path

from cli_driver_axiom.driver_state import check_status, write_pidfile


def test_status_missing_pidfile(tmp_path: Path) -> None:
    pidfile = tmp_path / "cli-driver-axiom.pid"
    st = check_status(pidfile, pid_exists=lambda _pid: True)
    assert st.running is False
    assert st.pid is None
    assert st.stale_pidfile is False


def test_status_running(tmp_path: Path) -> None:
    pidfile = tmp_path / "cli-driver-axiom.pid"
    write_pidfile(pidfile, 123)
    st = check_status(pidfile, pid_exists=lambda pid: pid == 123)
    assert st.running is True
    assert st.pid == 123
    assert st.stale_pidfile is False


def test_status_stale_pidfile(tmp_path: Path) -> None:
    pidfile = tmp_path / "cli-driver-axiom.pid"
    write_pidfile(pidfile, 99999)
    st = check_status(pidfile, pid_exists=lambda _pid: False)
    assert st.running is False
    assert st.pid == 99999
    assert st.stale_pidfile is True

