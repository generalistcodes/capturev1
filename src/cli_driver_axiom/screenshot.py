from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import mss
import mss.tools


@dataclass(frozen=True)
class Region:
    left: int
    top: int
    width: int
    height: int

    def to_monitor_dict(self) -> Dict[str, int]:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}


def list_monitors(*, mss_factory: Callable[[], Any] = mss.mss) -> List[Dict[str, int]]:
    """
    Returns the MSS `monitors` list (index 0 is the virtual bounding box, 1..N are displays).
    """
    with mss_factory() as sct:
        return [dict(m) for m in sct.monitors]


def select_monitor(
    monitors: List[Dict[str, int]], *, display: int
) -> Dict[str, int]:
    if display < 0:
        raise ValueError("display must be >= 0")
    if display >= len(monitors):
        raise ValueError(f"display {display} not available; found {len(monitors) - 1} displays")
    return monitors[display]


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def capture_png(
    *,
    out_path: Path,
    display: int = 1,
    region: Optional[Region] = None,
    mss_factory: Callable[[], Any] = mss.mss,
) -> Path:
    """
    Captures a screenshot to `out_path` (PNG). By default captures display 1.

    Notes:
    - `display=0` captures the "virtual screen" (bounding box of all monitors) per MSS.
    - If `region` is provided, it is used as the grab rectangle (absolute coordinates).
    """
    ensure_parent_dir(out_path)

    with mss_factory() as sct:
        monitors = [dict(m) for m in sct.monitors]
        grab_rect = region.to_monitor_dict() if region else select_monitor(monitors, display=display)
        shot = sct.grab(grab_rect)

        png_bytes = mss.tools.to_png(shot.rgb, shot.size)
        out_path.write_bytes(png_bytes)

    return out_path

