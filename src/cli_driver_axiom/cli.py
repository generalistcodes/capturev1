from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import os
import time

import typer
from rich.console import Console
from rich.table import Table

from cli_driver_axiom.config import resolve_capture, resolve_driver
from cli_driver_axiom.driver_state import check_status, write_pidfile
from cli_driver_axiom.screenshot import Region, capture_png, list_monitors


app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _timestamp_name(prefix: str = "axiom_") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}{ts}.png"


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
    interval: Optional[float] = typer.Option(
        None,
        "--interval",
        "-i",
        help="Capture interval in seconds. If omitted, uses $AXIOM_INTERVAL_SECONDS or 5.0.",
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
    )

    count = 0
    try:
        while True:
            out_path = _resolve_out_path(out=None, out_dir=resolved.out_dir, prefix=resolved.filename_prefix)
            saved = capture_png(out_path=out_path, display=resolved.display, region=resolved.region)
            count += 1
            console.print(f"[dim]{count}[/dim] Saved: [bold]{saved}[/bold]")
            if max_shots is not None and count >= max_shots:
                break
            time.sleep(resolved.interval_seconds)
    except KeyboardInterrupt:
        console.print("Stopping driver...")
    finally:
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
            cli_interval_seconds=1.0,
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

