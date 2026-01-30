from __future__ import annotations

import pytest

from cli_driver_axiom.durations import parse_duration_seconds


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("10", 10.0),
        ("10s", 10.0),
        ("1m", 60.0),
        ("2h", 7200.0),
        ("1d", 86400.0),
        ("1.5m", 90.0),
        ("  5  ", 5.0),
        ("  5S  ", 5.0),
    ],
)
def test_parse_duration_seconds(raw: str, expected: float) -> None:
    assert parse_duration_seconds(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "-1s", "0", "1w", "1ms", "1m30s"])
def test_parse_duration_seconds_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_duration_seconds(raw)

