from unittest.mock import patch

import pytest

from mnamer.endpoints import anidb_anime, anilist_media, anilist_search
from mnamer.exceptions import MnamerNotFoundException
from mnamer.metadata import MetadataEpisode
from mnamer.providers import AniDB, AniList

pytestmark = pytest.mark.local

ANIDB_XML = """
<anime id="42">
  <startdate>2020-01-01</startdate>
  <description>An anime synopsis.</description>
  <titles>
    <title xml:lang="ja" type="main">アニメ</title>
    <title xml:lang="en" type="official">Anime Title</title>
  </titles>
  <episodes>
    <episode id="100">
      <epno type="1">1</epno>
      <airdate>2020-01-08</airdate>
      <title xml:lang="en" type="official">First Episode</title>
    </episode>
    <episode id="101">
      <epno type="2">1</epno>
      <airdate>2020-02-01</airdate>
      <title xml:lang="en" type="official">Special Episode</title>
    </episode>
  </episodes>
</anime>
"""

ANILIST_MEDIA = {
    "id": 123,
    "title": {
        "romaji": "Anime Title",
        "english": "Anime Title",
        "native": "アニメ",
        "userPreferred": "Anime Title",
    },
    "description": "An anime synopsis.",
    "startDate": {"year": 2020, "month": 1, "day": 1},
    "episodes": 12,
    "externalLinks": [{"site": "ANIDB", "url": "https://anidb.net/anime/42"}],
}


@patch("mnamer.endpoints.request_json")
def test_anilist_media__normalizes_graphql_response(mock_request):
    mock_request.return_value = (200, {"data": {"Media": ANILIST_MEDIA}})

    result = anilist_media(123, cache=False)

    assert result == ANILIST_MEDIA
    _, kwargs = mock_request.call_args
    assert kwargs["body"]["variables"] == {"id": 123}


@patch("mnamer.endpoints.request_json")
def test_anilist_search__requires_results(mock_request):
    mock_request.return_value = (200, {"data": {"Page": {"media": []}}})

    with pytest.raises(MnamerNotFoundException):
        anilist_search("missing", cache=False)


@patch("mnamer.endpoints.request_text")
def test_anidb_anime__parses_titles_and_episode_numbers(mock_request):
    mock_request.return_value = (200, ANIDB_XML)

    result = anidb_anime("mnamer", 1, 42, cache=False)

    assert result["id"] == "42"
    assert result["title"] == "Anime Title"
    assert result["episodes"][0] == {
        "id": "100",
        "number": 1,
        "type": "1",
        "air_date": "2020-01-08",
        "title": "First Episode",
    }


@patch("mnamer.providers.anilist_search")
def test_anilist_provider__searches_title_and_preserves_requested_season(mock_search):
    mock_search.return_value = {"media": [ANILIST_MEDIA]}
    query = MetadataEpisode(series="Anime Title", season=2, episode=3)

    results = list(AniList(cache=False).search(query))

    assert len(results) == 1
    assert results[0].id_anilist == 123
    assert results[0].id_anidb == "42"
    assert results[0].season == 2
    assert results[0].episode == 3
    assert results[0].title == "Episode 03"


@patch("mnamer.providers.anidb_anime")
def test_anidb_provider__returns_episode_metadata(mock_anime):
    mock_anime.return_value = {
        "id": "42",
        "title": "Anime Title",
        "synopsis": "An anime synopsis.",
        "episodes": [
            {
                "id": "100",
                "number": 1,
                "type": "1",
                "air_date": "2020-01-08",
                "title": "First Episode",
            }
        ],
    }
    query = MetadataEpisode(id_anidb="42", season=1, episode=1)

    result = next(AniDB("mnamer", cache=False).search(query))

    assert result.series == "Anime Title"
    assert result.title == "First Episode"
    assert result.id_anidb == "42"
    assert str(result.date) == "2020-01-08"
    mock_anime.assert_called_once_with(
        "mnamer", 1, "42", language=None, cache=False
    )
