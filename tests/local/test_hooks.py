from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mnamer.hooks import HookResult, run_success_hook
from mnamer.metadata import MetadataMovie
from mnamer.setting_store import SettingStore
from mnamer.target import Target
from mnamer.types import MediaType

pytestmark = pytest.mark.local


def test_hook_passes_media_context_without_a_shell(tmp_path):
    source = tmp_path / "incoming.mkv"
    destination = tmp_path / "library" / "Movie.mkv"
    metadata = MetadataMovie(name="Movie", year=2024, id_tmdb="42")
    completed = SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("mnamer.hooks.subprocess.run", return_value=completed) as run:
        result = run_success_hook(
            "refresh-library --quiet", source, destination, metadata
        )

    assert result == HookResult()
    args, kwargs = run.call_args
    assert args[0] == ["refresh-library", "--quiet"]
    assert kwargs["shell"] is not True
    environment = kwargs["env"]
    assert environment["MNAMER_SOURCE_PATH"] == str(source.absolute())
    assert environment["MNAMER_TARGET_PATH"] == str(destination.absolute())
    assert environment["MNAMER_MEDIA_TYPE"] == "movie"
    assert environment["MNAMER_ID_TMDB"] == "42"


def test_hook_failure_is_non_fatal():
    completed = SimpleNamespace(returncode=7, stdout="", stderr="refresh failed")
    metadata = MetadataMovie(name="Movie", year=2024)

    with patch("mnamer.hooks.subprocess.run", return_value=completed):
        result = run_success_hook(
            "refresh-library", Path("source"), Path("target"), metadata
        )

    assert result.error == "command exited with status 7: refresh failed"


def test_hook_rejects_invalid_or_empty_commands():
    metadata = MetadataMovie(name="Movie", year=2024)

    assert (
        "invalid command"
        in run_success_hook('"broken', Path("a"), Path("b"), metadata).error
    )
    assert (
        run_success_hook("", Path("a"), Path("b"), metadata).error == "command is empty"
    )


def test_relocate_runs_hook_after_the_move(tmp_path):
    source = tmp_path / "input.mkv"
    source.write_bytes(b"video")
    settings = SettingStore(media=MediaType.MOVIE, on_success="refresh-library")
    target = Target(source, settings)
    target.metadata = MetadataMovie(name="Movie", year=2024, container=".mkv")

    with (
        patch("mnamer.target.record_move") as record_move,
        patch("mnamer.target.run_success_hook", return_value=HookResult()) as hook,
    ):
        target.relocate()

    destination = tmp_path / "Movie (2024).mkv"
    assert not source.exists()
    assert destination.read_bytes() == b"video"
    record_move.assert_called_once_with(source, destination.resolve())
    hook.assert_called_once_with(
        "refresh-library", source, destination.resolve(), target.metadata
    )
