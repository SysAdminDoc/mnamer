"""Optional ffmpeg-backed thumbnail generation for relocated media."""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path
from shutil import which

THUMBNAIL_TIMEOUT_SECONDS = 120.0


@dataclasses.dataclass(frozen=True)
class ThumbnailResult:
    path: Path | None = None
    error: str | None = None


def _escape_drawtext(value: str) -> str:
    """Escape text for ffmpeg's drawtext filter without invoking a shell."""
    escaped = value.replace("\\", "\\\\")
    for character in (":", "'", ",", "[", "]"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\n", " ").replace("\r", " ")


def create_thumbnail(
    source: Path,
    destination: Path,
    label: str,
    width: int = 640,
    executable: str | None = None,
) -> ThumbnailResult:
    """Extract a representative frame and burn the matched title into it."""
    if width < 1:
        return ThumbnailResult(error="thumbnail width must be positive")
    ffmpeg = executable or which("ffmpeg")
    if not ffmpeg:
        return ThumbnailResult(error="ffmpeg executable not found")
    destination.parent.mkdir(parents=True, exist_ok=True)
    video_filter = (
        "thumbnail,"
        f"scale=w='min({width},iw)':h=-2,"
        "drawtext=fontcolor=white:fontsize=24:box=1:boxcolor=black@0.65:"
        f"boxborderw=8:x=20:y=h-th-20:text='{_escape_drawtext(label)}'"
    )
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        "00:00:05",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        video_filter,
        str(destination),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
            text=True,
            timeout=THUMBNAIL_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return ThumbnailResult(error="ffmpeg executable not found")
    except subprocess.TimeoutExpired:
        return ThumbnailResult(
            error=f"ffmpeg timed out after {THUMBNAIL_TIMEOUT_SECONDS:g}s"
        )
    except OSError as error:
        return ThumbnailResult(error=str(error))
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        return ThumbnailResult(error=f"ffmpeg failed with status {error.returncode}{suffix}")
    if not destination.exists():
        detail = (result.stderr or result.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        return ThumbnailResult(error=f"ffmpeg did not create thumbnail{suffix}")
    return ThumbnailResult(path=destination)
