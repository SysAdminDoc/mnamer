from unittest.mock import patch

import pytest

from mnamer.endpoints import musicbrainz_recording, musicbrainz_search
from mnamer.metadata import MetadataMusic
from mnamer.providers import MusicBrainz
from mnamer.setting_store import SettingStore
from mnamer.target import Target

pytestmark = pytest.mark.local

RECORDING = {
    "id": "b8a9f1f8-1e5f-4a85-9f5c-1c6e3f3a2c4b",
    "title": "Come Together",
    "artist-credit": [{"name": "The Beatles", "joinphrase": ""}],
    "first-release-date": "1969-09-26",
    "releases": [{"title": "Abbey Road", "date": "1969-09-26"}],
}


@patch("mnamer.endpoints.request_json")
def test_musicbrainz_search__uses_recording_query_and_descriptive_user_agent(
    mock_request,
):
    mock_request.return_value = (200, {"recordings": [RECORDING]})

    result = musicbrainz_search(
        title="Come Together",
        artist="The Beatles",
        album="Abbey Road",
        limit=5,
        cache=False,
    )

    assert result["recordings"] == [RECORDING]
    args, kwargs = mock_request.call_args
    assert args[0].endswith("/recording")
    assert kwargs["parameters"] == {
        "query": 'recording:"Come Together" AND artist:"The Beatles" AND '
        'release:"Abbey Road"',
        "fmt": "json",
        "limit": 5,
    }
    assert kwargs["headers"]["user-agent"].startswith("mnamer/")
    assert kwargs["cache"] is False


@patch("mnamer.endpoints.request_json")
def test_musicbrainz_recording__requests_json_release_data(mock_request):
    mock_request.return_value = (200, RECORDING)

    result = musicbrainz_recording(RECORDING["id"], cache=False)

    assert result == RECORDING
    _, kwargs = mock_request.call_args
    assert kwargs["parameters"] == {
        "fmt": "json",
        "inc": "artist-credits+releases",
    }


@patch("mnamer.providers.musicbrainz_search")
def test_musicbrainz_provider__normalizes_recording_metadata(mock_search):
    mock_search.return_value = {"recordings": [RECORDING]}
    query = MetadataMusic(artist="The Beatles", album="Abbey Road", title="Come Together")

    result = next(MusicBrainz(cache=False).search(query))

    assert result.artist == "The Beatles"
    assert result.album == "Abbey Road"
    assert result.title == "Come Together"
    assert result.year == 1969
    assert result.id_musicbrainz == RECORDING["id"]


def test_target__detects_music_container_and_extracts_track_fields(tmp_path):
    source = tmp_path / "The Beatles - Abbey Road - 01 - Come Together.mp3"

    target = Target(source, SettingStore())

    assert isinstance(target.metadata, MetadataMusic)
    assert target.metadata.artist == "The Beatles"
    assert target.metadata.album == "Abbey Road"
    assert target.metadata.track == 1
    assert target.metadata.title == "Come Together"
    assert format(target.metadata) == (
        "The Beatles - Abbey Road - 01 - Come Together"
    )
