from unittest.mock import patch

import pytest

from mnamer.endpoints import fanart_images
from mnamer.exceptions import MnamerNetworkException
from mnamer.setting_store import SettingStore
from mnamer.target import Target
from mnamer.types import ProviderType

pytestmark = pytest.mark.local

ARTWORK_RESPONSE = {
    "movieposter": [
        {
            "url": "https://assets.fanart.tv/poster.png",
            "lang": "en",
            "likes": "4",
        }
    ],
    "moviebackground": [
        {
            "url": "https://assets.fanart.tv/fanart.jpg",
            "lang": "00",
            "likes": "2",
        }
    ],
    "hdmovielogo": [
        {
            "url": "https://assets.fanart.tv/logo.png",
            "lang": "en",
            "likes": "1",
        }
    ],
}


@patch("mnamer.endpoints.request_json")
def test_fanart_images__uses_movie_resource_and_api_header(mock_request):
    mock_request.return_value = (200, ARTWORK_RESPONSE)

    result = fanart_images("key", "movie", 550, cache=False)

    assert result == ARTWORK_RESPONSE
    args, kwargs = mock_request.call_args
    url = args[0]
    assert url.endswith("/movies/550")
    assert kwargs["headers"] == {"api-key": "key"}
    assert kwargs["cache"] is False


@patch("mnamer.target.fanart_image")
@patch("mnamer.target.fanart_images")
def test_target__relocate_downloads_artwork_alongside_movie(
    mock_images, mock_image, tmp_path
):
    mock_images.return_value = ARTWORK_RESPONSE
    mock_image.side_effect = lambda url, cache: url.encode()
    source = tmp_path / "the.goonies.1985.mp4"
    source.touch()
    settings = SettingStore(
        api_key_fanart="key",
        artwork=True,
        id_tmdb="550",
        movie_api=ProviderType.TMDB,
    )
    target = Target(source, settings)

    target.relocate()

    destination = tmp_path / "The Goonies (1985).mp4"
    assert destination.exists()
    assert not source.exists()
    assert (tmp_path / "poster.png").read_bytes() == b"https://assets.fanart.tv/poster.png"
    assert (tmp_path / "fanart.jpg").exists()
    assert (tmp_path / "logo.png").exists()
    assert len(target.artwork_downloaded) == 3


@patch("mnamer.target.fanart_images")
def test_target__artwork_failure_does_not_block_relocation(mock_images, tmp_path):
    mock_images.side_effect = MnamerNetworkException("service unavailable")
    source = tmp_path / "the.goonies.1985.mp4"
    source.touch()
    settings = SettingStore(
        api_key_fanart="key",
        artwork=True,
        id_tmdb="550",
        movie_api=ProviderType.TMDB,
    )
    target = Target(source, settings)

    target.relocate()

    assert (tmp_path / "The Goonies (1985).mp4").exists()
    assert target.artwork_error == "service unavailable"
