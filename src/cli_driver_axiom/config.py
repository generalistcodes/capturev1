from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from cli_driver_axiom.durations import parse_duration_seconds
from cli_driver_axiom.screenshot import Region


ENV_OUT_DIR = "AXIOM_OUT_DIR"
ENV_INTERVAL_SECONDS = "AXIOM_INTERVAL_SECONDS"
ENV_DISPLAY = "AXIOM_DISPLAY"
ENV_REGION = "AXIOM_REGION"
ENV_PIDFILE = "AXIOM_PIDFILE"
ENV_FILENAME_PREFIX = "AXIOM_FILENAME_PREFIX"
ENV_CHECKPOINT_CSV = "AXIOM_CHECKPOINT_CSV"


@dataclass(frozen=True)
class ResolvedCapture:
    out_dir: Path
    display: int
    region: Optional[Region]
    filename_prefix: str


@dataclass(frozen=True)
class ResolvedDriver(ResolvedCapture):
    interval_seconds: float
    pidfile: Optional[Path]
    checkpoint_csv: Path


def _env(name: str) -> Optional[str]:
    val = os.getenv(name)
    if val is None:
        return None
    val = val.strip()
    return val or None


def _parse_int(value: Optional[str], *, name: str) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as e:
        raise ValueError(f"{name} must be an integer") from e


def _parse_float(value: Optional[str], *, name: str) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError as e:
        raise ValueError(f"{name} must be a number") from e


def parse_region_tokens(tokens: List[int]) -> Region:
    if len(tokens) != 4:
        raise ValueError("region requires exactly 4 integers: x y width height")
    x, y, w, h = tokens
    if w <= 0 or h <= 0:
        raise ValueError("region width/height must be > 0")
    return Region(left=int(x), top=int(y), width=int(w), height=int(h))


def parse_region_string(value: Optional[str]) -> Optional[Region]:
    if value is None:
        return None
    cleaned = value.replace(",", " ").strip()
    if not cleaned:
        return None
    parts = cleaned.split()
    try:
        nums = [int(p) for p in parts]
    except ValueError as e:
        raise ValueError(f"{ENV_REGION} must be 4 integers like 'x y w h' or 'x,y,w,h'") from e
    return parse_region_tokens(nums)


def resolve_capture(
    *,
    cli_out_dir: Optional[Path],
    cli_display: Optional[int],
    cli_region: Optional[List[int]],
    cwd: Path,
) -> ResolvedCapture:
    env_out_dir = _env(ENV_OUT_DIR)
    out_dir = (cli_out_dir or (Path(env_out_dir) if env_out_dir else None) or cwd).expanduser()

    env_display = _parse_int(_env(ENV_DISPLAY), name=ENV_DISPLAY)
    display = cli_display if cli_display is not None else (env_display if env_display is not None else 1)
    if display < 0:
        raise ValueError("display must be >= 0")

    filename_prefix = _env(ENV_FILENAME_PREFIX) or "axiom_"

    region: Optional[Region]
    if cli_region is not None:
        region = parse_region_tokens(cli_region)
    else:
        region = parse_region_string(_env(ENV_REGION))

    return ResolvedCapture(out_dir=out_dir, display=display, region=region, filename_prefix=filename_prefix)


def resolve_driver(
    *,
    cli_out_dir: Optional[Path],
    cli_display: Optional[int],
    cli_region: Optional[List[int]],
    cli_interval_seconds: Optional[str],
    cli_pidfile: Optional[Path],
    cwd: Path,
) -> ResolvedDriver:
    cap = resolve_capture(
        cli_out_dir=cli_out_dir, cli_display=cli_display, cli_region=cli_region, cwd=cwd
    )

    env_interval_raw = _env(ENV_INTERVAL_SECONDS)
    cli_interval_raw = cli_interval_seconds
    raw = cli_interval_raw if cli_interval_raw is not None else (env_interval_raw if env_interval_raw is not None else "5")
    try:
        interval_seconds = parse_duration_seconds(raw)
    except ValueError as e:
        raise ValueError(f"{ENV_INTERVAL_SECONDS} invalid: {e}") from e

    env_pidfile = _env(ENV_PIDFILE)
    pidfile = (cli_pidfile or (Path(env_pidfile) if env_pidfile else None) or (cap.out_dir / "cli-driver-axiom.pid"))
    pidfile = pidfile.expanduser()

    env_csv = _env(ENV_CHECKPOINT_CSV)
    checkpoint_csv = (Path(env_csv) if env_csv else (cap.out_dir / "axiom_checkpoints.csv")).expanduser()

    return ResolvedDriver(
        out_dir=cap.out_dir,
        display=cap.display,
        region=cap.region,
        filename_prefix=cap.filename_prefix,
        interval_seconds=interval_seconds,
        pidfile=pidfile,
        checkpoint_csv=checkpoint_csv,
    )

