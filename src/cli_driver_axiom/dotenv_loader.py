from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class DotenvResult:
    path: Path
    loaded: Dict[str, str]


def _strip_quotes(val: str) -> str:
    v = val.strip()
    if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        return v[1:-1]
    return v


def parse_dotenv_lines(lines: Iterable[str]) -> Dict[str, str]:
    """
    Minimal .env parser:
    - supports KEY=VALUE (VALUE may be quoted)
    - ignores blank lines and comments starting with #
    - does not support export, multiline, or variable expansion
    """
    out: Dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        out[key] = _strip_quotes(val)
    return out


def find_default_env_file(cwd: Path) -> Optional[Path]:
    """
    Default lookup order (first hit wins):
    - ./ .env
    - ./ axiom.env
    """
    candidates = [cwd / ".env", cwd / "axiom.env"]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def load_env_file(
    path: Path,
    *,
    environ: Dict[str, str],
    override: bool = False,
) -> DotenvResult:
    data = parse_dotenv_lines(path.read_text(encoding="utf-8").splitlines())
    loaded: Dict[str, str] = {}
    for k, v in data.items():
        if override or (k not in environ):
            environ[k] = v
            loaded[k] = v
    return DotenvResult(path=path, loaded=loaded)

