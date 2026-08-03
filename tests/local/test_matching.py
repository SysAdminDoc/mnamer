from unittest.mock import patch

import pytest

import mnamer.matching as matching
from mnamer.metadata import MetadataMovie
from mnamer.providers import Tmdb

pytestmark = pytest.mark.local


@patch("mnamer.providers.tmdb_search_movies")
def test_tmdb_provider__searches_adjacent_release_years(mock_search):
    searched_years = []

    def search(*args, **kwargs):
        year = args[2]
        searched_years.append(year)
        return {
            "results": [
                {
                    "id": year,
                    "title": "Example",
                    "overview": "An example movie.",
                    "release_date": f"{year}-01-01",
                }
            ],
            "total_pages": 1,
        }

    mock_search.side_effect = search
    query = MetadataMovie(name="Example", year="2020")

    results = list(Tmdb(cache=False).search(query))

    assert searched_years == [2020, 2019, 2021]
    assert [result.year for result in results] == [2020, 2019, 2021]


def test_rank_matches__semantic_title_score(monkeypatch):
    class FakeModel:
        def encode(self, titles, normalize_embeddings):
            assert normalize_embeddings is True
            vectors = {
                "Mangled Release": [1.0, 0.0],
                "Unrelated Movie": [0.0, 1.0],
                "Correct Catalog Title": [0.9, 0.1],
            }
            return [vectors[title] for title in titles]

    monkeypatch.setattr(matching, "_MODEL", FakeModel())
    monkeypatch.setattr(matching, "_MODEL_INITIALIZED", True)
    query = MetadataMovie(name="Mangled Release")
    matches = [
        MetadataMovie(name="Unrelated Movie"),
        MetadataMovie(name="Correct Catalog Title"),
    ]

    assert [match.name for match in matching.rank_matches(query, matches)] == [
        "Correct Catalog Title",
        "Unrelated Movie",
    ]
