from unittest.mock import patch

import pytest

from mnamer.endpoints import omdb_search, omdb_title
from mnamer.exceptions import MnamerException, MnamerNotFoundException
from mnamer.providers import Omdb
from tests import JUNK_TEXT, MockRequestResponse, assert_has_keys

pytestmark = [
    pytest.mark.network,
    pytest.mark.omdb,
    pytest.mark.flaky(reruns=1),
]


@patch("mnamer.utils.requests_cache.CachedSession.request")
def test_omdb_title__title_id_xnor__title(mock_request):
    mock_response = MockRequestResponse(200, '{"key":"value"}')
    mock_request.return_value = mock_response
    omdb_title(Omdb.api_key, title="some title")


@patch("mnamer.utils.requests_cache.CachedSession.request")
def test_omdb_title__title_id_xnor__id(mock_request):
    mock_response = MockRequestResponse(200, '{"key":"value"}')
    mock_request.return_value = mock_response
    omdb_title(Omdb.api_key, id_imdb="tt123")


@patch("mnamer.utils.requests_cache.CachedSession.request")
def test_omdb_title__title_id_xnor__both(mock_request):
    mock_response = MockRequestResponse(200, '{"key":"value"}')
    mock_request.return_value = mock_response
    with pytest.raises(MnamerException):
        omdb_title(Omdb.api_key, title="some title", id_imdb="tt123")


@patch("mnamer.utils.requests_cache.CachedSession.request")
def test_omdb_title__title_id_xnor__neither(mock_request):
    mock_response = MockRequestResponse(200, '{"key":"value"}')
    mock_request.return_value = mock_response
    with pytest.raises(MnamerException):
        omdb_title(Omdb.api_key)


def test_omdb_title__media__movie():
    expected_top_level_keys = {
        "actors",
        "awards",
        "box_office",
        "country",
        "director",
        "dvd",
        "genre",
        "imdb_id",
        "imdb_rating",
        "imdb_votes",
        "language",
        "metascore",
        "plot",
        "poster",
        "production",
        "rated",
        "ratings",
        "released",
        "response",
        "runtime",
        "title",
        "type",
        "website",
        "writer",
        "year",
    }
    result = omdb_title(Omdb.api_key, media="movie", title="ninja turtles")
    assert_has_keys(result, expected_top_level_keys)
    assert result["response"]
    assert result["type"] == "movie"
    assert result["title"] == "Teenage Mutant Ninja Turtles"


def test_omdb_title__media__series():
    expected_top_level_keys = {
        "actors",
        "awards",
        "country",
        "director",
        "genre",
        "imdb_id",
        "imdb_rating",
        "imdb_votes",
        "language",
        "metascore",
        "plot",
        "poster",
        "rated",
        "ratings",
        "released",
        "response",
        "runtime",
        "title",
        "total_seasons",
        "type",
        "writer",
        "year",
    }

    result = omdb_title(Omdb.api_key, media="series", title="ninja turtles")
    assert_has_keys(result, expected_top_level_keys)
    assert result["response"]
    assert result["type"] == "series"
    assert result["title"] == "Teenage Mutant Ninja Turtles"


def test_omdb_title__api_key_fail():
    with pytest.raises(MnamerException):
        omdb_title(JUNK_TEXT, title="uhf", cache=False)


def test_omdb_title__id_imdb_fail():
    with pytest.raises(MnamerException):
        omdb_title(Omdb.api_key, "")


def test_omdb_title__not_found():
    with pytest.raises(MnamerNotFoundException):
        omdb_title(Omdb.api_key, "1" * 2)


def test_omdb_title__invalid_plot():
    with pytest.raises(MnamerException):
        omdb_title(Omdb.api_key, title="uhf", plot="medium")


def test_omdb_search__fields__top_level():
    expected_fields = {"search", "response", "total_results"}
    result = omdb_search(Omdb.api_key, "ninja turtles")
    assert_has_keys(result, expected_fields)


def test_omdb_search__fields__search():
    expected_fields = {"title", "year", "imdb_id", "type", "poster"}
    result = omdb_search(Omdb.api_key, "ninja turtles")["search"][0]
    assert_has_keys(result, expected_fields)


def test_omdb_search__query__movie():
    result = omdb_search(Omdb.api_key, "ninja turtles", media="movie")
    assert all(entry["type"] == "movie" for entry in result["search"])


def test_omdb_search__query__series():
    result = omdb_search(Omdb.api_key, "ninja turtles", media="series")
    assert all(entry["type"] == "series" for entry in result["search"])


def test_omdb_search__api_key_fail():
    with pytest.raises(MnamerException):
        omdb_search(JUNK_TEXT, "ninja turtles", cache=False)


def test_omdb_search__query__fail():
    with pytest.raises(MnamerNotFoundException):
        omdb_search(Omdb.api_key, JUNK_TEXT, cache=False)


def test_omdb_search__year():
    result = omdb_search(Omdb.api_key, "ninja turtles", year=1987)
    assert "tt0131613" == result["search"][0]["imdb_id"]


def test_omdb_search__page_diff():
    p1 = omdb_search(Omdb.api_key, "Dogs", page=1)
    p2 = omdb_search(Omdb.api_key, "Dogs", page=2)
    assert p1 != p2


def test_omdb_search__page_out_of_bounds():
    with pytest.raises(MnamerException):
        omdb_search(Omdb.api_key, "Super Mario", page=101)
