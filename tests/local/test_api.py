from unittest.mock import patch

from mnamer.api import preview_path, process_path
from mnamer.metadata import MetadataMovie
from mnamer.setting_store import SettingStore
from mnamer.target import Target


def test_preview_path_returns_match_without_relocation(tmp_path):
    source = tmp_path / "the.goonies.1985.mp4"
    source.write_bytes(b"video")
    settings = SettingStore()
    match = MetadataMovie(name="The Goonies", year="1985", container=".mp4")

    with patch.object(Target, "query", return_value=[match]):
        preview = preview_path(source, settings)

    assert preview.matches == (match,)
    assert preview.destination == tmp_path / "The Goonies (1985).mp4"
    assert source.exists()


def test_process_path_uses_library_surface(tmp_path):
    source = tmp_path / "the.goonies.1985.mp4"
    source.write_bytes(b"video")
    settings = SettingStore()
    match = MetadataMovie(name="The Goonies", year="1985", container=".mp4")

    with (
        patch.object(Target, "query", return_value=[match]),
        patch("mnamer.target.record_move"),
    ):
        destination = process_path(source, settings)

    assert destination == tmp_path / "The Goonies (1985).mp4"
    assert destination.read_bytes() == b"video"
    assert not source.exists()
