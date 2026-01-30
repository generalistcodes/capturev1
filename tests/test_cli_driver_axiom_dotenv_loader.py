from __future__ import annotations

from pathlib import Path

import pytest

from cli_driver_axiom.dotenv_loader import find_default_env_file, load_env_file, parse_dotenv_lines


def test_parse_dotenv_lines_basic() -> None:
    data = parse_dotenv_lines(
        [
            "# comment",
            "",
            "AXIOM_INTERVAL_SECONDS=10s",
            "AXIOM_OUT_DIR=./captures",
            "QUOTED=\"hello\"",
            "SINGLE='world'",
        ]
    )
    assert data["AXIOM_INTERVAL_SECONDS"] == "10s"
    assert data["QUOTED"] == "hello"
    assert data["SINGLE"] == "world"


def test_load_env_file_does_not_override_existing(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("A=1\nB=2\n", encoding="utf-8")
    environ = {"A": "999"}
    res = load_env_file(env_path, environ=environ, override=False)
    assert environ["A"] == "999"
    assert environ["B"] == "2"
    assert "B" in res.loaded and "A" not in res.loaded


def test_find_default_env_file(tmp_path: Path) -> None:
    cwd = tmp_path
    assert find_default_env_file(cwd) is None
    (cwd / "axiom.env").write_text("A=1\n", encoding="utf-8")
    assert find_default_env_file(cwd) == cwd / "axiom.env"
    (cwd / ".env").write_text("A=2\n", encoding="utf-8")
    assert find_default_env_file(cwd) == cwd / ".env"

