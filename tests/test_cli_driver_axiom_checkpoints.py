from __future__ import annotations

from pathlib import Path

from cli_driver_axiom.checkpoints import CheckpointRow, append_checkpoint


def test_append_checkpoint_writes_header_once(tmp_path: Path) -> None:
    csv_path = tmp_path / "axiom_checkpoints.csv"
    append_checkpoint(
        csv_path,
        CheckpointRow(
            event="start",
            ts_utc="t1",
            count=0,
            filename="",
            out_dir="/out",
            interval_seconds="60",
            display="1",
            region="None",
            send="none",
        ),
    )
    append_checkpoint(
        csv_path,
        CheckpointRow(
            event="capture",
            ts_utc="t2",
            count=1,
            filename="a.png",
            out_dir="/out",
            interval_seconds="60",
            display="1",
            region="None",
            send="none",
        ),
    )

    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("event,ts_utc,count,filename")
    assert len(lines) == 3
