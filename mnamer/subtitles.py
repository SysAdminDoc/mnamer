from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mnamer.const import SUBTITLE_CONTAINERS
from mnamer.exceptions import MnamerException
from mnamer.language import Language

_MAX_BYTES = 256 * 1024
_MIN_ALPHABETIC_CHARACTERS = 24
_TEXT_SUBTITLE_CONTAINERS = tuple(
    container for container in SUBTITLE_CONTAINERS if container != ".idx"
)
_DETECTOR: Any = None
_DETECTOR_INITIALIZED = False


def _read_text(source: Path) -> str | None:
    if source.suffix.lower() not in _TEXT_SUBTITLE_CONTAINERS:
        return None
    try:
        with source.open("rb") as subtitle_file:
            raw = subtitle_file.read(_MAX_BYTES)
    except OSError:
        return None
    if not raw:
        return None

    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text
    return None


def _dialogue_text(text: str) -> str | None:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^\{\d+\}\{\d+\}", "", line)
        line = re.sub(r"<[^>]+>", " ", line)
        line = re.sub(r"\{[^}]*\}", " ", line)
        line = line.strip()
        if (
            not line
            or "-->" in line
            or line.isdigit()
            or line.casefold() in {"webvtt", "note", "style", "region"}
        ):
            continue
        lines.append(line)

    dialogue = " ".join(lines)
    alphabetic_characters = re.findall(r"[^\W\d_]", dialogue, re.UNICODE)
    if len(alphabetic_characters) < _MIN_ALPHABETIC_CHARACTERS:
        return None
    return dialogue


def _detector() -> Any:
    global _DETECTOR, _DETECTOR_INITIALIZED
    if _DETECTOR_INITIALIZED:
        return _DETECTOR
    _DETECTOR_INITIALIZED = True
    try:
        from lingua import Language as LinguaLanguage, LanguageDetectorBuilder
    except ImportError:
        return None

    supported = []
    for language in Language.all():
        lingua_language = getattr(LinguaLanguage, language.name.upper(), None)
        if lingua_language is not None and lingua_language.iso_code_639_1 is not None:
            supported.append(lingua_language)
    if not supported:
        return None
    _DETECTOR = (
        LanguageDetectorBuilder.from_languages(*supported)
        .with_minimum_relative_distance(0.2)
        .build()
    )
    return _DETECTOR


def detect_subtitle_language(source: Path) -> Language | None:
    """Detect a subtitle's language from dialogue text when no code is present."""
    text = _read_text(source)
    dialogue = _dialogue_text(text) if text else None
    if not dialogue:
        return None
    detector = _detector()
    if detector is None:
        return None
    try:
        detected = detector.detect_language_of(dialogue)
    except (RuntimeError, ValueError):
        return None
    if detected is None or detected.iso_code_639_1 is None:
        return None
    try:
        return Language.parse(detected.iso_code_639_1.name.lower())
    except MnamerException:
        return None
