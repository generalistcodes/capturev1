from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import subprocess

import pytest

from cli_driver_axiom.senders import CurlSendConfig, GitSendConfig, send_to_curl, send_to_git


class _Runner:
    def __init__(self) -> None:
        self.calls: List[List[str]] = []
        self.diff_cached_quiet_returncode = 1

    def __call__(self, args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        # emulate "git diff --cached --quiet"
        if list(args[:4]) == ["git", "diff", "--cached", "--quiet"]:
            return subprocess.CompletedProcess(args=list(args), returncode=self.diff_cached_quiet_returncode, stdout="", stderr="")
        return subprocess.CompletedProcess(args=list(args), returncode=0, stdout="", stderr="")


def test_send_to_git_runs_add_commit_push_when_changes() -> None:
    r = _Runner()
    cfg = GitSendConfig(repo_dir=Path("/repo"), remote="origin", branch="main", push=True)
    send_to_git(file_path=Path("/repo/a.png"), config=cfg, message="msg", run_cmd=r)

    assert r.calls[0][:3] == ["git", "rev-parse", "--is-inside-work-tree"]
    assert r.calls[1][:3] == ["git", "add", "--"]
    assert r.calls[2] == ["git", "diff", "--cached", "--quiet"]
    assert r.calls[3][:2] == ["git", "commit"]
    assert r.calls[4] == ["git", "push", "origin", "HEAD:main"]


def test_send_to_git_skips_commit_when_no_staged_changes() -> None:
    r = _Runner()
    r.diff_cached_quiet_returncode = 0  # no staged diff
    cfg = GitSendConfig(repo_dir=Path("/repo"), remote="origin", branch="main", push=True)
    send_to_git(file_path=Path("/repo/a.png"), config=cfg, message="msg", run_cmd=r)

    # rev-parse, add, diff --cached --quiet
    assert len(r.calls) == 3


def test_send_to_curl_builds_expected_args(tmp_path: Path) -> None:
    file_path = tmp_path / "a.png"
    file_path.write_bytes(b"x")

    r = _Runner()
    cfg = CurlSendConfig(url="https://example.invalid/upload", headers=["Authorization: Bearer X"])
    send_to_curl(file_path=file_path, config=cfg, run_cmd=r)

    assert r.calls
    args = r.calls[0]
    assert args[:6] == ["curl", "-sS", "-f", "-X", "POST", "-H"]
    assert "Authorization: Bearer X" in args
    assert any(a.startswith("file=@") for a in args)
    assert args[-1] == "https://example.invalid/upload"

