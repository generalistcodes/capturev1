from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import os
import time
import signal

import typer
from rich.console import Console
from rich.table import Table

from cli_driver_axiom.checkpoints import CheckpointRow, append_checkpoint, utc_now_iso
from cli_driver_axiom.config import resolve_capture, resolve_driver
from cli_driver_axiom.driver_state import check_status, write_pidfile
from cli_driver_axiom.senders import CurlSendConfig, GitSendConfig, send_to_curl, send_to_git
from cli_driver_axiom.screenshot import Region, capture_png, list_monitors


app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _timestamp_name(prefix: str = "axiom_") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}{ts}.png"


def _timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_out_path(*, out: Optional[Path], out_dir: Path, prefix: str) -> Path:
    if out:
        return out
    return out_dir / _timestamp_name(prefix=prefix)


def _resolve_cli_out_dir(*, out: Optional[Path], dir_: Optional[Path]) -> Optional[Path]:
    if out and dir_:
        raise typer.BadParameter("Use either --out or --dir (not both).")
    return dir_


@app.command()
def info() -> None:
    """
    Show available monitors/displays as detected by MSS.
    """
    monitors = list_monitors()
    table = Table(title="cli-driver-axiom displays")
    table.add_column("index", justify="right")
    table.add_column("left", justify="right")
    table.add_column("top", justify="right")
    table.add_column("width", justify="right")
    table.add_column("height", justify="right")

    for idx, m in enumerate(monitors):
        table.add_row(
            str(idx),
            str(m.get("left", "")),
            str(m.get("top", "")),
            str(m.get("width", "")),
            str(m.get("height", "")),
        )

    console.print(table)
    if len(monitors) > 1:
        console.print("Tip: use [bold]--display N[/bold] (1..N) to capture a specific display.")


@app.command()
def capture(
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output PNG path (defaults to ./axiom_<timestamp>.png).",
        dir_okay=False,
        writable=True,
        resolve_path=True,
    ),
    dir_: Optional[Path] = typer.Option(
        None,
        "--dir",
        help="Output directory (file name will be timestamped). If omitted, uses $AXIOM_OUT_DIR or current directory.",
        file_okay=False,
        writable=True,
        resolve_path=True,
    ),
    display: Optional[int] = typer.Option(
        None,
        "--display",
        "-d",
        min=0,
        help="Monitor index (0 = virtual screen, 1..N = displays). If omitted, uses $AXIOM_DISPLAY or 1.",
    ),
    region: Optional[List[int]] = typer.Option(
        None,
        "--region",
        help="Capture region: x y width height (absolute screen coordinates). If omitted, uses $AXIOM_REGION if set.",
    ),
    send: str = typer.Option(
        "none",
        "--send",
        help="Send captured file somewhere: none|git|curl.",
        case_sensitive=False,
    ),
    git_repo: Optional[Path] = typer.Option(
        None,
        "--git-repo",
        help="Git repo directory used for --send git (default: output directory).",
        file_okay=False,
        resolve_path=True,
    ),
    git_remote: str = typer.Option("origin", "--git-remote", help="Git remote name for --send git."),
    git_branch: str = typer.Option("main", "--git-branch", help="Git branch for --send git."),
    no_git_push: bool = typer.Option(
        False, "--no-git-push", help="Do not push when using --send git (commit only)."
    ),
    curl_url: Optional[str] = typer.Option(None, "--curl-url", help="URL for --send curl."),
    curl_header: Optional[List[str]] = typer.Option(
        None, "--curl-header", help="Extra header for curl upload (repeatable)."
    ),
) -> None:
    """
    Capture a screenshot to a PNG file.
    """
    cli_out_dir = _resolve_cli_out_dir(out=out, dir_=dir_)
    try:
        resolved = resolve_capture(
            cli_out_dir=cli_out_dir, cli_display=display, cli_region=region, cwd=Path.cwd()
        )
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e

    out_path = _resolve_out_path(out=out, out_dir=resolved.out_dir, prefix=resolved.filename_prefix)
    saved = capture_png(out_path=out_path, display=resolved.display, region=resolved.region)
    console.print(f"Saved screenshot: [bold]{saved}[/bold]")

    send_mode = (send or "none").lower()
    if send_mode == "none":
        return
    if send_mode == "git":
        repo_dir = git_repo or resolved.out_dir
        cfg = GitSendConfig(repo_dir=repo_dir, remote=git_remote, branch=git_branch, push=(not no_git_push))
        send_to_git(file_path=saved, config=cfg, message=f"capture {saved.name}")
        console.print(f"Sent via git: [bold]{cfg.remote}[/bold] [dim]{cfg.branch}[/dim]")
        return
    if send_mode == "curl":
        if not curl_url:
            raise typer.BadParameter("--curl-url is required when --send curl")
        cfg = CurlSendConfig(url=curl_url, headers=curl_header or [])
        send_to_curl(file_path=saved, config=cfg)
        console.print("Sent via curl upload.")
        return
    raise typer.BadParameter("--send must be one of: none, git, curl")


@app.command()
def driver(
    dir_: Optional[Path] = typer.Option(
        None,
        "--dir",
        help="Output directory. If omitted, uses $AXIOM_OUT_DIR or current directory.",
        file_okay=False,
        writable=True,
        resolve_path=True,
    ),
    interval: Optional[str] = typer.Option(
        None,
        "--interval",
        "-i",
        help="Capture interval (e.g. 10s, 1m, 2h). If omitted, uses $AXIOM_INTERVAL_SECONDS or 5s.",
    ),
    display: Optional[int] = typer.Option(
        None,
        "--display",
        "-d",
        min=0,
        help="Monitor index (0 = virtual screen, 1..N = displays). If omitted, uses $AXIOM_DISPLAY or 1.",
    ),
    region: Optional[List[int]] = typer.Option(
        None,
        "--region",
        help="Capture region: x y width height. If omitted, uses $AXIOM_REGION if set.",
    ),
    pidfile: Optional[Path] = typer.Option(
        None,
        "--pidfile",
        help="Optional pidfile path. If omitted, uses $AXIOM_PIDFILE if set.",
        dir_okay=False,
        writable=True,
        resolve_path=True,
    ),
    max_shots: Optional[int] = typer.Option(
        None,
        "--max-shots",
        help="Optional limit for number of captures (useful for smoke tests).",
        min=1,
    ),
    send: str = typer.Option(
        "none",
        "--send",
        help="Send each captured file somewhere: none|git|curl.",
        case_sensitive=False,
    ),
    git_repo: Optional[Path] = typer.Option(
        None,
        "--git-repo",
        help="Git repo directory used for --send git (default: output directory).",
        file_okay=False,
        resolve_path=True,
    ),
    git_remote: str = typer.Option("origin", "--git-remote", help="Git remote name for --send git."),
    git_branch: str = typer.Option("main", "--git-branch", help="Git branch for --send git."),
    no_git_push: bool = typer.Option(
        False, "--no-git-push", help="Do not push when using --send git (commit only)."
    ),
    git_push_every: int = typer.Option(
        1, "--git-push-every", min=1, help="Push every N captures when using --send git."
    ),
    curl_url: Optional[str] = typer.Option(None, "--curl-url", help="URL for --send curl."),
    curl_header: Optional[List[str]] = typer.Option(
        None, "--curl-header", help="Extra header for curl upload (repeatable)."
    ),
    checkpoint_csv: Optional[Path] = typer.Option(
        None,
        "--checkpoint-csv",
        help="Where to write checkpoint CSV (default: $AXIOM_CHECKPOINT_CSV or <out_dir>/axiom_checkpoints.csv).",
        dir_okay=False,
        resolve_path=True,
    ),
) -> None:
    """
    Run as a long-lived driver process that captures screenshots every N seconds.
    Stop with Ctrl+C.
    """
    try:
        resolved = resolve_driver(
            cli_out_dir=dir_,
            cli_display=display,
            cli_region=region,
            cli_interval_seconds=interval,
            cli_pidfile=pidfile,
            cwd=Path.cwd(),
        )
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e

    if checkpoint_csv is not None:
        resolved = type(resolved)(
            out_dir=resolved.out_dir,
            display=resolved.display,
            region=resolved.region,
            filename_prefix=resolved.filename_prefix,
            interval_seconds=resolved.interval_seconds,
            pidfile=resolved.pidfile,
            checkpoint_csv=checkpoint_csv,
        )

    # `resolve_driver` always sets a pidfile (defaulting to <out_dir>/cli-driver-axiom.pid).
    status = check_status(resolved.pidfile)
    if status.pid is not None and status.running:
        raise typer.BadParameter(f"driver already running (pid {status.pid}) per pidfile: {resolved.pidfile}")
    if resolved.pidfile.exists() and status.stale_pidfile:
        console.print(f"[yellow]Warning:[/yellow] removing stale pidfile: {resolved.pidfile}")
        try:
            resolved.pidfile.unlink()
        except OSError:
            pass
    write_pidfile(resolved.pidfile, os.getpid())

    console.print(
        "Driver started:"
        f"\n- out_dir: [bold]{resolved.out_dir}[/bold]"
        f"\n- interval: [bold]{resolved.interval_seconds}[/bold] seconds"
        f"\n- display: [bold]{resolved.display}[/bold]"
        f"\n- region: [bold]{resolved.region}[/bold]"
        f"\n- pidfile: [bold]{resolved.pidfile}[/bold]"
        f"\n- checkpoint_csv: [bold]{resolved.checkpoint_csv}[/bold]"
    )

    send_mode = (send or "none").lower()
    git_cfg: Optional[GitSendConfig] = None
    curl_cfg: Optional[CurlSendConfig] = None
    if send_mode == "git":
        repo_dir = git_repo or resolved.out_dir
        git_cfg = GitSendConfig(repo_dir=repo_dir, remote=git_remote, branch=git_branch, push=(not no_git_push))
    elif send_mode == "curl":
        if not curl_url:
            raise typer.BadParameter("--curl-url is required when --send curl")
        curl_cfg = CurlSendConfig(url=curl_url, headers=curl_header or [])
    elif send_mode != "none":
        raise typer.BadParameter("--send must be one of: none, git, curl")

    stop_requested = {"value": False}

    def _request_stop(_signum: int, _frame: object) -> None:
        stop_requested["value"] = True

    try:
        signal.signal(signal.SIGTERM, _request_stop)
        signal.signal(signal.SIGINT, _request_stop)
    except Exception:
        # Best-effort; some environments may not allow signal registration.
        pass

    count = 0
    append_checkpoint(
        resolved.checkpoint_csv,
        CheckpointRow(
            event="start",
            ts_utc=utc_now_iso(),
            count=0,
            filename="",
            out_dir=str(resolved.out_dir),
            interval_seconds=str(resolved.interval_seconds),
            display=str(resolved.display),
            region=str(resolved.region),
            send=send_mode,
        ),
    )
    try:
        while True:
            if stop_requested["value"]:
                break
            out_path = _resolve_out_path(out=None, out_dir=resolved.out_dir, prefix=resolved.filename_prefix)
            saved = capture_png(out_path=out_path, display=resolved.display, region=resolved.region)
            count += 1
            console.print(f"[dim]{count}[/dim] Saved: [bold]{saved}[/bold]")

            if git_cfg is not None:
                push_now = git_cfg.push and (count % git_push_every == 0)
                cfg = GitSendConfig(
                    repo_dir=git_cfg.repo_dir,
                    remote=git_cfg.remote,
                    branch=git_cfg.branch,
                    push=push_now,
                )
                send_to_git(file_path=saved, config=cfg, message=f"capture {saved.name}")
            elif curl_cfg is not None:
                send_to_curl(file_path=saved, config=curl_cfg)

            append_checkpoint(
                resolved.checkpoint_csv,
                CheckpointRow(
                    event="capture",
                    ts_utc=utc_now_iso(),
                    count=count,
                    filename=saved.name,
                    out_dir=str(resolved.out_dir),
                    interval_seconds=str(resolved.interval_seconds),
                    display=str(resolved.display),
                    region=str(resolved.region),
                    send=send_mode,
                ),
            )

            if max_shots is not None and count >= max_shots:
                break
            # Sleep in small chunks so SIGTERM can stop quickly.
            remaining = resolved.interval_seconds
            while remaining > 0 and not stop_requested["value"]:
                chunk = 0.5 if remaining > 0.5 else remaining
                time.sleep(chunk)
                remaining -= chunk
    finally:
        append_checkpoint(
            resolved.checkpoint_csv,
            CheckpointRow(
                event="stop",
                ts_utc=utc_now_iso(),
                count=count,
                filename="",
                out_dir=str(resolved.out_dir),
                interval_seconds=str(resolved.interval_seconds),
                display=str(resolved.display),
                region=str(resolved.region),
                send=send_mode,
            ),
        )
        if resolved.pidfile.exists():
            try:
                resolved.pidfile.unlink()
            except OSError:
                pass


@app.command()
def status(
    pidfile: Optional[Path] = typer.Option(
        None,
        "--pidfile",
        help="Pidfile path to check. If omitted, uses $AXIOM_PIDFILE or <out_dir>/cli-driver-axiom.pid when --dir provided.",
        dir_okay=False,
        resolve_path=True,
    ),
    dir_: Optional[Path] = typer.Option(
        None,
        "--dir",
        help="Output directory to derive default pidfile (<dir>/cli-driver-axiom.pid).",
        file_okay=False,
        resolve_path=True,
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only use exit code; print nothing."),
) -> None:
    """
    Check whether the driver is running.

    Exit codes:
    - 0: running
    - 1: not running (or missing pidfile)
    """
    # Reuse resolve_driver to honor env vars and defaults, but allow status to be used
    # without providing interval/region/display.
    try:
        resolved = resolve_driver(
            cli_out_dir=dir_,
            cli_display=None,
            cli_region=None,
            cli_interval_seconds="1",
            cli_pidfile=pidfile,
            cwd=Path.cwd(),
        )
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e

    st = check_status(resolved.pidfile)
    if st.running:
        if not quiet:
            console.print(f"[green]RUNNING[/green] pid={st.pid} pidfile={st.pidfile}")
        raise typer.Exit(code=0)

    if not quiet:
        if st.pid is None:
            console.print(f"[red]NOT RUNNING[/red] (pidfile missing/empty) pidfile={st.pidfile}")
        elif st.stale_pidfile:
            console.print(f"[red]NOT RUNNING[/red] (stale pidfile) pid={st.pid} pidfile={st.pidfile}")
        else:
            console.print(f"[red]NOT RUNNING[/red] pidfile={st.pidfile}")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

