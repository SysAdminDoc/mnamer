"""Importable preview and relocation API for library integrations."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from mnamer.exceptions import MnamerException, MnamerNotFoundException
from mnamer.metadata import Metadata
from mnamer.setting_store import SettingStore
from mnamer.target import Target


@dataclasses.dataclass(frozen=True)
class Preview:
    """Metadata candidates and destination calculated for one target."""

    target: Target
    matches: tuple[Metadata, ...]

    @property
    def destination(self) -> Path | None:
        return self.target.destination if self.matches else None

    @property
    def metadata(self) -> Metadata:
        return self.target.metadata


def preview_target(target: Target) -> Preview:
    """Query a target and return its candidates without moving the file."""
    matches = tuple(target.query())
    if matches:
        target.metadata.update(matches[0])
    return Preview(target=target, matches=matches)


def preview_path(path: str | Path, settings: SettingStore | None = None) -> Preview:
    """Create a target from a path and return a non-mutating preview result."""
    return preview_target(Target(Path(path), settings or SettingStore()))


def process_target(target: Target) -> Path:
    """Resolve and relocate a target using the supplied settings."""
    preview = preview_target(target)
    if not preview.matches and target._settings.no_guess:
        raise MnamerNotFoundException
    if target.destination == target.source:
        raise MnamerException("source and destination paths are the same")
    if target._settings.no_overwrite and target.destination.exists():
        raise MnamerException("destination already exists")
    target.relocate()
    return target.destination


def process_path(path: str | Path, settings: SettingStore | None = None) -> Path:
    """Create, resolve, and relocate a target from a path."""
    target = Target(Path(path), settings or SettingStore())
    return process_target(target)


__all__ = ["Preview", "preview_path", "preview_target", "process_path", "process_target"]
