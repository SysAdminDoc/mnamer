import sys
from unittest.mock import patch

import pytest

from mnamer.setting_store import SettingStore
from mnamer.types import MediaType, ProviderType
from tests import DEFAULT_SETTINGS

pytestmark = pytest.mark.local


@pytest.mark.parametrize(
    "item", DEFAULT_SETTINGS.items(), ids=tuple(DEFAULT_SETTINGS.keys())
)
def test_as_dict(item):
    settings = SettingStore()
    k, v = item
    assert settings.as_dict()[k] == v


@pytest.mark.parametrize(
    "api", (ProviderType.TMDB, ProviderType.OMDB), ids=("TMDB", "OMDB")
)
def test_api_for__movie(api: ProviderType):
    settings = SettingStore(movie_api=api)
    assert settings.api_for(MediaType.MOVIE) is api


@pytest.mark.parametrize("api", ProviderType)
def test_api_key_for(api: ProviderType):
    settings = SettingStore()
    setattr(settings, f"api_key_{api.value}", "xxx")
    assert settings.api_key_for(api) == "xxx"


def test_smart_match_flag():
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--smart-match"]):
        settings.load()

    assert settings.smart_match is True


def test_tui_flag():
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--tui"]):
        settings.load()

    assert settings.tui is True


def test_watch_flag():
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--watch"]):
        settings.load()

    assert settings.watch is True


def test_undo_flag():
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--undo"]):
        settings.load()

    assert settings.undo is True


def test_on_success_flag():
    settings = SettingStore()
    with patch.object(
        sys,
        "argv",
        ["mnamer", "--on-success", "refresh-library --quiet"],
    ):
        settings.load()

    assert settings.on_success == "refresh-library --quiet"


def test_dry_run_diff_flag():
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--dry-run-diff"]):
        settings.load()

    assert settings.dry_run_diff is True


def test_log_format_flag():
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--log-format", "json"]):
        settings.load()

    assert settings.log_format == "json"


def test_serve_flags():
    settings = SettingStore()
    with patch.object(
        sys,
        "argv",
        ["mnamer", "--serve", "--serve-host", "0.0.0.0", "--serve-port", "9000"],
    ):
        settings.load()

    assert settings.serve is True
    assert settings.serve_host == "0.0.0.0"
    assert settings.serve_port == 9000


def test_thumbnail_flags():
    settings = SettingStore()
    with patch.object(
        sys,
        "argv",
        ["mnamer", "--thumbnails", "--thumbnail-width", "320"],
    ):
        settings.load()

    assert settings.thumbnails is True
    assert settings.thumbnail_width == 320


def test_toml_config_supports_comments_and_trailing_commas(tmp_path):
    config = tmp_path / ".mnamer-v2.toml"
    config.write_text(
        """
# Batch settings may be annotated.
batch = true
mask = ["mkv", "srt",]
movie_format = "{name} ({year}).{extension}"
""",
        encoding="utf-8",
    )
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--config-path", str(config)]):
        settings.load()

    assert settings.batch is True
    assert settings.mask == [".mkv", ".srt"]


def test_json_config_remains_compatible(tmp_path):
    config = tmp_path / ".mnamer-v2.json"
    config.write_text('{"batch": true, "mask": ["mp4"]}', encoding="utf-8")
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--config-path", str(config)]):
        settings.load()

    assert settings.batch is True
    assert settings.mask == [".mp4"]


def test_config_can_clear_list_values(tmp_path):
    config = tmp_path / ".mnamer-v2.toml"
    config.write_text("mask = []\nignore = []\n", encoding="utf-8")
    settings = SettingStore()
    with patch.object(sys, "argv", ["mnamer", "--config-path", str(config)]):
        settings.load()

    assert settings.mask == []
    assert settings.ignore == []
