import json
from unittest.mock import patch

import pytest

from mnamer.metadata import MetadataEpisode, MetadataMovie, MetadataMusic
from mnamer.setting_store import SettingStore
from mnamer.target import Target

pytestmark = pytest.mark.local


def test_target__uses_adjacent_movie_nfo_before_online_provider(tmp_path):
    source = tmp_path / "The Goonies.1985.mp4"
    source.touch()
    source.with_suffix(".nfo").write_text(
        """
        <movie>
          <title>The Goonies</title>
          <year>1985</year>
          <plot>A group of friends find a pirate treasure map.</plot>
          <uniqueid type="imdb">tt0089218</uniqueid>
          <uniqueid type="tmdb">9340</uniqueid>
        </movie>
        """,
        encoding="utf-8",
    )

    target = Target(source, SettingStore())
    with patch.object(target._provider, "search", side_effect=AssertionError):
        result = target.query()[0]

    assert isinstance(result, MetadataMovie)
    assert result.name == "The Goonies"
    assert result.year == 1985
    assert result.id_imdb == "tt0089218"
    assert result.id_tmdb == "9340"
    assert result.synopsis.startswith("A group")


def test_target__uses_episode_nfo_ids_and_air_date(tmp_path):
    source = tmp_path / "The Bear.S02E03.mkv"
    source.touch()
    source.with_suffix(".nfo").write_text(
        """
        <episodedetails>
          <showtitle>The Bear</showtitle>
          <title>Sundae</title>
          <season>2</season>
          <episode>3</episode>
          <aired>2023-07-05</aired>
          <uniqueid type="tvdb">12345</uniqueid>
        </episodedetails>
        """,
        encoding="utf-8",
    )

    target = Target(source, SettingStore())
    with patch.object(target._provider, "search", side_effect=AssertionError):
        result = target.query()[0]

    assert isinstance(result, MetadataEpisode)
    assert result.series == "The Bear"
    assert result.season == 2
    assert result.episode == 3
    assert str(result.date) == "2023-07-05"
    assert result.title == "Sundae"
    assert result.id_tvdb == "12345"


def test_target__uses_jellyfin_json_provider_ids_for_music(tmp_path):
    source = tmp_path / "The Beatles - Abbey Road - 01 - Come Together.mp3"
    source.touch()
    source.with_suffix(".json").write_text(
        json.dumps(
            {
                "Name": "Come Together",
                "Album": "Abbey Road",
                "AlbumArtist": "The Beatles",
                "IndexNumber": 1,
                "PremiereDate": "1969-09-26",
                "ProviderIds": {
                    "MusicBrainzTrack": "b8a9f1f8-1e5f-4a85-9f5c-1c6e3f3a2c4b"
                },
            }
        ),
        encoding="utf-8",
    )

    target = Target(source, SettingStore())
    with patch.object(target._provider, "search", side_effect=AssertionError):
        result = target.query()[0]

    assert isinstance(result, MetadataMusic)
    assert result.artist == "The Beatles"
    assert result.album == "Abbey Road"
    assert result.track == 1
    assert result.title == "Come Together"
    assert result.year == 1969
    assert result.id_musicbrainz == "b8a9f1f8-1e5f-4a85-9f5c-1c6e3f3a2c4b"


def test_target__falls_back_to_online_provider_without_sidecar(tmp_path):
    source = tmp_path / "The Goonies.1985.mp4"
    source.touch()
    target = Target(source, SettingStore())
    online_result = MetadataMovie(name="The Goonies", year=1985)

    with patch.object(target._provider, "search", return_value=[online_result]):
        assert target.query() == [online_result]
