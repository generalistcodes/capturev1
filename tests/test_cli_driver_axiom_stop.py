from __future__ import annotations

from typing import List, Tuple

from cli_driver_axiom.driver_state import stop_pid


def test_stop_pid_term_success() -> None:
    calls: List[Tuple[int, int]] = []
    alive = {"value": True}

    def pid_exists(_pid: int) -> bool:
        return alive["value"]

    def kill_func(pid: int, sig: int) -> None:
        calls.append((pid, sig))
        # simulate graceful exit on SIGTERM
        alive["value"] = False

    ok = stop_pid(123, timeout_seconds=0.5, force=False, pid_exists=pid_exists, kill_func=kill_func)
    assert ok is True
    assert calls and calls[0][0] == 123


def test_stop_pid_force_kill() -> None:
    calls: List[Tuple[int, int]] = []
    # stays alive until SIGKILL
    state = {"alive": True}

    def pid_exists(_pid: int) -> bool:
        return state["alive"]

    def kill_func(_pid: int, sig: int) -> None:
        calls.append((_pid, sig))
        if sig != 15:  # not SIGTERM
            state["alive"] = False

    ok = stop_pid(123, timeout_seconds=0.1, force=True, pid_exists=pid_exists, kill_func=kill_func)
    assert ok is True
    assert len(calls) >= 2
