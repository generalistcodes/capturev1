from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from cli_driver_axiom.config import (
    ENV_DISPLAY,
    ENV_INTERVAL_SECONDS,
    ENV_OUT_DIR,
    ENV_REGION,
    resolve_capture,
    resolve_driver,
)
from cli_driver_axiom.screenshot import Region, capture_png, select_monitor


def test_select_monitor_valid() -> None:
    monitors = [
        {"left": 0, "top": 0, "width": 2000, "height": 1000},  # virtual
        {"left": 0, "top": 0, "width": 1000, "height": 1000},
        {"left": 1000, "top": 0, "width": 1000, "height": 1000},
    ]
    assert select_monitor(monitors, display=1)["width"] == 1000
    assert select_monitor(monitors, display=2)["left"] == 1000


def test_select_monitor_invalid() -> None:
    monitors = [{"left": 0, "top": 0, "width": 1, "height": 1}]
    with pytest.raises(ValueError):
        select_monitor(monitors, display=-1)
    with pytest.raises(ValueError):
        select_monitor(monitors, display=1)


@dataclass
class _FakeShot:
    rgb: bytes
    size: Tuple[int, int]


class _FakeMSS:
    def __init__(self, monitors: List[Dict[str, int]]):
        self.monitors = monitors
        self.last_grab_rect: Dict[str, int] | None = None

    def __enter__(self) -> "_FakeMSS":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    def grab(self, rect: Dict[str, int]) -> _FakeShot:
        self.last_grab_rect = dict(rect)
        w = int(rect["width"])
        h = int(rect["height"])
        # 3 bytes per pixel (RGB). Solid black.
        return _FakeShot(rgb=b"\x00" * (w * h * 3), size=(w, h))


def test_capture_png_writes_file(tmp_path: Path) -> None:
    monitors = [
        {"left": 0, "top": 0, "width": 200, "height": 100},  # virtual
        {"left": 0, "top": 0, "width": 200, "height": 100},
    ]
    fake = _FakeMSS(monitors)

    out = tmp_path / "out.png"
    saved = capture_png(out_path=out, display=1, mss_factory=lambda: fake)
    assert saved == out
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_capture_png_region_overrides_display(tmp_path: Path) -> None:
    monitors = [
        {"left": 0, "top": 0, "width": 200, "height": 100},  # virtual
        {"left": 0, "top": 0, "width": 200, "height": 100},
    ]
    fake = _FakeMSS(monitors)

    out = tmp_path / "region.png"
    region = Region(left=10, top=11, width=12, height=13)
    capture_png(out_path=out, display=1, region=region, mss_factory=lambda: fake)
    assert fake.last_grab_rect == {"left": 10, "top": 11, "width": 12, "height": 13}


def test_resolve_capture_env_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_OUT_DIR, str(tmp_path))
    monkeypatch.setenv(ENV_DISPLAY, "2")
    monkeypatch.setenv(ENV_REGION, "1 2 3 4")

    resolved = resolve_capture(cli_out_dir=None, cli_display=None, cli_region=None, cwd=Path("/cwd"))
    assert resolved.out_dir == tmp_path
    assert resolved.display == 2
    assert resolved.region == Region(left=1, top=2, width=3, height=4)


def test_resolve_driver_interval_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_OUT_DIR, str(tmp_path))
    monkeypatch.setenv(ENV_INTERVAL_SECONDS, "10")

    resolved = resolve_driver(
        cli_out_dir=None,
        cli_display=None,
        cli_region=None,
        cli_interval_seconds=2.5,
        cli_pidfile=None,
        cwd=Path("/cwd"),
    )
    assert resolved.interval_seconds == 2.5

