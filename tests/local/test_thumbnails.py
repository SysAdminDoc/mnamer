from pathlib import Path
from unittest.mock import patch

from mnamer.metadata import MetadataMovie
from mnamer.setting_store import SettingStore
from mnamer.target import Target
from mnamer.thumbnails import ThumbnailResult, create_thumbnail


def test_create_thumbnail_builds_burned_in_ffmpeg_command(tmp_path):
    source = tmp_path / "source.mkv"
    destination = tmp_path / "Movie.jpg"
    source.write_bytes(b"video")

    def fake_run(command, **_kwargs):
        Path(command[-1]).touch()
        return type("Completed", (), {"stdout": "", "stderr": ""})()

    with (
        patch("mnamer.thumbnails.which", return_value="ffmpeg"),
        patch("mnamer.thumbnails.subprocess.run", side_effect=fake_run) as run,
    ):
        result = create_thumbnail(source, destination, "Movie: 2024", width=320)

    assert result == ThumbnailResult(path=destination)
    command = run.call_args.args[0]
    assert command[0] == "ffmpeg"
    assert "scale=w='min(320,iw)':h=-2" in command[command.index("-vf") + 1]
    assert "Movie\\: 2024" in command[command.index("-vf") + 1]


def test_create_thumbnail_reports_missing_ffmpeg(tmp_path):
    with patch("mnamer.thumbnails.which", return_value=None):
        result = create_thumbnail(
            tmp_path / "source.mkv", tmp_path / "Movie.jpg", "Movie"
        )

    assert result.path is None
    assert result.error == "ffmpeg executable not found"


def test_relocate_thumbnail_failure_does_not_block_move(tmp_path):
    source = tmp_path / "the.goonies.1985.mp4"
    source.write_bytes(b"video")
    settings = SettingStore(thumbnails=True)
    target = Target(source, settings)
    target.metadata = MetadataMovie(name="The Goonies", year="1985", container=".mp4")

    with patch(
        "mnamer.target.create_thumbnail",
        return_value=ThumbnailResult(error="ffmpeg executable not found"),
    ):
        target.relocate()

    destination = tmp_path / "The Goonies (1985).mp4"
    assert destination.exists()
    assert not source.exists()
    assert target.thumbnail_error == "ffmpeg executable not found"
