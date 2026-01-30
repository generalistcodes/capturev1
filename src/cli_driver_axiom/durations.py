from __future__ import annotations

import re


_DURATION_RE = re.compile(r"^\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>[smhdSMHD]?)\s*$")


def parse_duration_seconds(value: str) -> float:
    """
    Parses a duration string into seconds.

    Supported:
    - "10"   -> 10 seconds
    - "10s"  -> 10 seconds
    - "1m"   -> 60 seconds
    - "2h"   -> 7200 seconds
    - "1d"   -> 86400 seconds
    - "1.5m" -> 90 seconds
    """
    m = _DURATION_RE.match(value)
    if not m:
        raise ValueError("invalid duration (expected like 10, 10s, 1m, 2h, 1d)")

    num = float(m.group("num"))
    unit = (m.group("unit") or "s").lower()
    if num <= 0:
        raise ValueError("duration must be > 0")

    mult = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}[unit]
    return num * mult

