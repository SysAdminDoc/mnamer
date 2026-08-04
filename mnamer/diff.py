"""Unified diff formatting for planned media relocations."""

from __future__ import annotations

from difflib import unified_diff
from pathlib import Path


def relocation_diff(source: Path, destination: Path) -> str:
    """Render one source-to-destination plan as a copyable unified diff."""
    source_text = f"{source.absolute()}\n"
    destination_text = f"{destination.absolute()}\n"
    return "".join(
        unified_diff(
            [source_text],
            [destination_text],
            fromfile="source",
            tofile="destination",
            n=0,
        )
    ).rstrip("\n")
