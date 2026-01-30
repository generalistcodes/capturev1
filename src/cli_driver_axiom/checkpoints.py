from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CheckpointRow:
    event: str  # start | capture | stop
    ts_utc: str
    count: int
    filename: str
    out_dir: str
    interval_seconds: str
    display: str
    region: str
    send: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "event": self.event,
            "ts_utc": self.ts_utc,
            "count": str(self.count),
            "filename": self.filename,
            "out_dir": self.out_dir,
            "interval_seconds": self.interval_seconds,
            "display": self.display,
            "region": self.region,
            "send": self.send,
        }


CSV_FIELDS = [
    "event",
    "ts_utc",
    "count",
    "filename",
    "out_dir",
    "interval_seconds",
    "display",
    "region",
    "send",
]


def append_checkpoint(csv_path: Path, row: CheckpointRow) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(row.as_dict())

