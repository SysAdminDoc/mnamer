from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

_HDR_PATTERNS = (
    ("HDR10+", re.compile(r"(?<![A-Z0-9])HDR10(?:\+|PLUS)(?![A-Z0-9])", re.I)),
    (
        "DV",
        re.compile(r"(?<![A-Z0-9])(?:DV|DOVI|DOLBY[\s._-]*VISION)(?![A-Z0-9])", re.I),
    ),
    ("HDR10", re.compile(r"(?<![A-Z0-9])HDR10(?![A-Z0-9+])", re.I)),
    ("HLG", re.compile(r"(?<![A-Z0-9])HLG(?![A-Z0-9])", re.I)),
    ("HDR", re.compile(r"(?<![A-Z0-9])HDR(?![A-Z0-9])", re.I)),
)
_ATMOS_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?:ATMOS|DOLBY[\s._-]*ATMOS)(?![A-Z0-9])", re.I
)


def _tags_from_text(text: str) -> tuple[str | None, str | None]:
    hdr_tags = []
    for tag, pattern in _HDR_PATTERNS:
        if pattern.search(text) and tag not in hdr_tags:
            hdr_tags.append(tag)
    hdr = " ".join(hdr_tags) or None
    audio = "Atmos" if _ATMOS_PATTERN.search(text) else None
    return hdr, audio


def _ffprobe(source: Path) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if not executable or not source.is_file():
        return {}
    try:
        result = subprocess.run(
            [
                executable,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(source),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0 or not result.stdout:
        return {}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _probe_tags(probe: dict[str, Any]) -> tuple[str | None, str | None]:
    text = json.dumps(probe, default=str)
    hdr, audio = _tags_from_text(text)
    streams = probe.get("streams", [])
    if not isinstance(streams, list):
        return hdr, audio
    for stream in streams:
        if not isinstance(stream, dict) or stream.get("codec_type") != "video":
            continue
        transfer = str(stream.get("color_transfer", "")).casefold()
        if transfer == "smpte2084" and hdr is None:
            hdr = "HDR10"
        elif transfer == "arib-std-b67" and hdr is None:
            hdr = "HLG"
    return hdr, audio


def detect_media_tags(
    source: Path, guessit_data: dict[str, Any]
) -> tuple[str | None, str | None]:
    """Extract HDR and audio tags from a release name and optional ffprobe data."""
    filename_hdr, filename_audio = _tags_from_text(source.name)
    guessit_text = json.dumps(guessit_data, default=str)
    data_hdr, data_audio = _tags_from_text(guessit_text)
    hdr = filename_hdr or data_hdr
    audio = filename_audio or data_audio
    if hdr and audio:
        return hdr, audio

    probe_hdr, probe_audio = _probe_tags(_ffprobe(source))
    return hdr or probe_hdr, audio or probe_audio
