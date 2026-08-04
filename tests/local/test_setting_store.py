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
