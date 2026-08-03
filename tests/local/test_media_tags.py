import json
from types import SimpleNamespace

import pytest

import mnamer.media_tags as media_tags
from mnamer.media_tags import detect_media_tags

pytestmark = pytest.mark.local


def test_detect_media_tags__filename_and_guessit_data(tmp_path):
    source = tmp_path / "Movie.2024.HDR10+.DV.Atmos.mkv"

    assert detect_media_tags(
        source,
        {"other": ["HDR10", "Dolby Vision"], "audio_codec": "Dolby Atmos"},
    ) == ("HDR10+ DV", "Atmos")


def test_detect_media_tags__ffprobe(monkeypatch, tmp_path):
    source = tmp_path / "Movie.2024.mkv"
    source.write_bytes(b"not a real video")
    probe = {
        "streams": [
            {"codec_type": "video", "color_transfer": "smpte2084"},
            {"codec_type": "audio", "tags": {"title": "Dolby Atmos"}},
        ]
    }
    monkeypatch.setattr(media_tags.shutil, "which", lambda _: "ffprobe.exe")
    monkeypatch.setattr(
        media_tags.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(probe)),
    )

    assert detect_media_tags(source, {}) == ("HDR10", "Atmos")
