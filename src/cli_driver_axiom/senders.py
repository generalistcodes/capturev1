from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence


@dataclass(frozen=True)
class GitSendConfig:
    repo_dir: Path
    remote: str = "origin"
    branch: str = "main"
    push: bool = True


@dataclass(frozen=True)
class CurlSendConfig:
    url: str
    headers: List[str]
    method: str = "POST"
    field_name: str = "file"


RunCmd = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


def _run_cmd(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
    )


def _require_ok(result: subprocess.CompletedProcess[str], *, what: str) -> None:
    if result.returncode == 0:
        return
    msg = (
        f"{what} failed (exit {result.returncode}).\n"
        f"cmd: {result.args}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )
    raise RuntimeError(msg)


def send_to_git(
    *,
    file_path: Path,
    config: GitSendConfig,
    message: str,
    run_cmd: RunCmd = _run_cmd,
) -> None:
    """
    Add `file_path` to git, commit, and optionally push.

    Requirements:
    - `config.repo_dir` must be a git working tree with `remote` configured.
    - authentication must already be configured (SSH key or token).
    """
    repo = config.repo_dir

    # Verify repo
    res = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], repo)
    _require_ok(res, what="git rev-parse")

    # Stage file (use relative path if possible)
    rel = file_path
    try:
        rel = file_path.relative_to(repo)
    except ValueError:
        rel = file_path

    res = run_cmd(["git", "add", "--", str(rel)], repo)
    _require_ok(res, what="git add")

    # If nothing staged, skip commit/push
    res = run_cmd(["git", "diff", "--cached", "--quiet"], repo)
    if res.returncode == 0:
        return
    if res.returncode != 1:
        _require_ok(res, what="git diff --cached")

    res = run_cmd(["git", "commit", "-m", message], repo)
    _require_ok(res, what="git commit")

    if config.push:
        res = run_cmd(["git", "push", config.remote, f"HEAD:{config.branch}"], repo)
        _require_ok(res, what="git push")


def send_to_curl(
    *,
    file_path: Path,
    config: CurlSendConfig,
    run_cmd: RunCmd = _run_cmd,
) -> None:
    """
    Send a file using `curl` as multipart form upload.
    """
    args: List[str] = ["curl", "-sS", "-f", "-X", config.method]
    for h in config.headers:
        args.extend(["-H", h])
    args.extend(["-F", f"{config.field_name}=@{file_path}"])
    args.append(config.url)

    res = run_cmd(args, Path.cwd())
    _require_ok(res, what="curl upload")

