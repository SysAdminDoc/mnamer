from unittest.mock import patch

import pytest

from mnamer.exceptions import MnamerNetworkException
from mnamer.metadata import MetadataMusic
from mnamer.providers import MusicBrainz

pytestmark = pytest.mark.local


def test_provider__opens_circuit_after_consecutive_network_failures():
    provider = MusicBrainz(cache=False)
    query = MetadataMusic(title="Chapter One")

    with patch(
        "mnamer.providers.musicbrainz_search",
        side_effect=MnamerNetworkException("service unavailable"),
    ) as mock_search:
        for _ in range(3):
            with pytest.raises(MnamerNetworkException, match="service unavailable"):
                next(provider.search(query))

        with pytest.raises(MnamerNetworkException, match="circuit is open"):
            next(provider.search(query))

    assert mock_search.call_count == 3


def test_provider__successful_half_open_request_resets_circuit():
    provider = MusicBrainz(cache=False)
    query = MetadataMusic(title="Chapter One")
    recording = {
        "id": "b8a9f1f8-1e5f-4a85-9f5c-1c6e3f3a2c4b",
        "title": "Chapter One",
    }

    with patch(
        "mnamer.providers.musicbrainz_search",
        side_effect=[
            MnamerNetworkException("service unavailable"),
            MnamerNetworkException("service unavailable"),
            MnamerNetworkException("service unavailable"),
            {"recordings": [recording]},
            MnamerNetworkException("service unavailable"),
        ],
    ):
        for _ in range(3):
            with pytest.raises(MnamerNetworkException):
                next(provider.search(query))
        provider._circuit_opened_at = 0

        result = next(provider.search(query))
        assert result.title == "Chapter One"

        with pytest.raises(MnamerNetworkException, match="service unavailable"):
            next(provider.search(query))
