from pathlib import Path

import pytest

from mnamer.metadata import MetadataEpisode
from mnamer.setting_store import SettingStore
from mnamer.target import Target

pytestmark = pytest.mark.local


@pytest.mark.parametrize(
    "filename",
    (
        "Show.S01E01E02.mkv",
        "Show - E01-E02.mkv",
        "Show.s01e01-e02.mkv",
    ),
)
def test_target__preserves_multi_episode_numbers(filename):
    target = Target(Path(filename), SettingStore())

    assert isinstance(target.metadata, MetadataEpisode)
    assert target.metadata.episodes == [1, 2]
    assert target.metadata.episode == 1
    assert format(target.metadata, "{series} {episode_range}") == "Show 01-02"
