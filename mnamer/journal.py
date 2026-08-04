"""Recoverable move journaling for CLI relocation sessions."""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import shutil
from pathlib import Path
from uuid import uuid4

from mnamer.const import CACHE_PATH

JOURNAL_PATH = CACHE_PATH / "moves.jsonl"
JOURNAL_RETENTION = 5


@dataclasses.dataclass(frozen=True)
class MoveRecord:
    source: Path
    destination: Path


@dataclasses.dataclass(frozen=True)
class UndoResult:
    moved: int = 0
    skipped: int = 0


def _archive_path(index: int) -> Path:
    return JOURNAL_PATH.with_name(f"{JOURNAL_PATH.stem}.{index}{JOURNAL_PATH.suffix}")


def _write_record(record: dict[str, object]) -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL_PATH.open("a", encoding="utf-8") as journal:
        journal.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
        journal.write("\n")


def start_session() -> None:
    """Rotate the previous session and create a fresh current journal."""
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    for index in range(JOURNAL_RETENTION - 1, 0, -1):
        archive = _archive_path(index)
        if archive.exists():
            archive.replace(_archive_path(index + 1))
    if JOURNAL_PATH.exists():
        JOURNAL_PATH.replace(_archive_path(1))
    _write_record(
        {
            "type": "session",
            "id": uuid4().hex,
            "started_at": dt.datetime.now(dt.UTC).isoformat(),
        }
    )


def record_move(source: Path, destination: Path) -> None:
    """Append a successful relocation to the active session journal."""
    if not JOURNAL_PATH.exists():
        return
    try:
        _write_record(
            {
                "type": "move",
                "source": str(source.absolute()),
                "destination": str(destination.absolute()),
            }
        )
    except OSError:
        # A successful relocation must not be reported as failed solely because
        # the cache became unavailable after the move completed.
        return


def _records() -> list[dict[str, object]]:
    try:
        lines = JOURNAL_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def last_session_moves() -> list[MoveRecord]:
    """Return current-session moves unless that session was already undone."""
    records = _records()
    if any(record.get("type") == "undo" for record in records):
        return []
    moves = []
    for record in records:
        if record.get("type") != "move":
            continue
        source = record.get("source")
        destination = record.get("destination")
        if not isinstance(source, str) or not isinstance(destination, str):
            continue
        moves.append(MoveRecord(Path(source), Path(destination)))
    return moves


def undo_last_session() -> UndoResult:
    """Move every recorded destination back to its original source safely."""
    moves = last_session_moves()
    moved = 0
    skipped = 0
    for record in reversed(moves):
        if not record.destination.exists() or record.source.exists():
            skipped += 1
            continue
        try:
            record.source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(record.destination), str(record.source))
        except OSError:
            skipped += 1
        else:
            moved += 1
    if moves and moved and not skipped:
        _write_record(
            {
                "type": "undo",
                "completed_at": dt.datetime.now(dt.UTC).isoformat(),
                "moved": moved,
            }
        )
    return UndoResult(moved=moved, skipped=skipped)
