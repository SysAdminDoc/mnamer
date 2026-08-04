import datetime as dt
from typing import Any, NamedTuple

from mnamer.const import MUSIC_CONTAINERS, SUBTITLE_CONTAINERS
from mnamer.language import Language
from mnamer.types import ProviderType

DEFAULT_SETTINGS = {
    "batch": False,
    "config_dump": False,
    "config_ignore": False,
    "dry_run_diff": False,
    "episode_api": ProviderType.TVMAZE,
    "episode_directory": None,
    "episode_format": "{series} - S{season:02}E{episode:02} - {title}.{extension}",
    "hits": 5,
    "id_imdb": None,
    "id_tmdb": None,
    "id_tvdb": None,
    "id_tvmaze": None,
    "id_musicbrainz": None,
    "ignore": [".*sample.*", "^RARBG.*"],
    "lower": False,
    "log_format": "text",
    "mask": [".avi", ".m4v", ".mp4", ".mkv", ".ts", ".wmv"]
    + SUBTITLE_CONTAINERS
    + MUSIC_CONTAINERS,
    "media": None,
    "movie_api": ProviderType.TMDB,
    "movie_directory": None,
    "movie_format": "{name} ({year}).{extension}",
    "music_api": ProviderType.MUSICBRAINZ,
    "music_directory": None,
    "music_format": "{artist} - {album} - {track:02} - {title}.{extension}",
    "no_cache": False,
    "no_guess": False,
    "no_overwrite": False,
    "no_style": False,
    "on_success": None,
    "preset": None,
    "recurse": False,
    "replace_after": {"&": "and", ";": ",", "@": "at"},
    "replace_before": {},
    "scene": False,
    "serve": False,
    "serve_host": "127.0.0.1",
    "serve_port": 8765,
    "smart_match": False,
    "targets": [],
    "test": False,
    "thumbnail_width": 640,
    "thumbnails": False,
    "tui": False,
    "undo": False,
    "watch": False,
    "verbose": False,
    "version": False,
}


JUNK_TEXT = "blablablabla"

EPISODE_META = {
    "The Walking Dead": {
        "date": dt.date(2015, 2, 22),
        "episode": 11,
        "id_imdb": "tt1520211",
        "id_tvdb": 153021,
        "id_tvmaze": 73,
        "media": "television",
        "season": 5,
        "series": "The Walking Dead",
        "title": "The Distance",
    },
    "Downtown": {
        "date": dt.date(1999, 11, 8),
        "episode": 13,
        "id_imdb": "tt0208616",
        "id_tvdb": 78342,
        "id_tvmaze": 30436,
        "media": "television",
        "season": 1,
        "series": "Downtown",
        "title": "Trip or Treat",
    },
    "Fargo": {
        "date": dt.date(2015, 10, 19),
        "episode": 2,
        "id_imdb": "tt2802850",
        "id_tvdb": 269613,
        "id_tvmaze": 32,
        "media": "television",
        "season": 2,
        "series": "Fargo",
        "title": "Before the Law",
    },
}

MOVIE_META = {
    "Idiocracy": {
        "id_imdb": "tt0387808",
        "id_tmdb": 7512,
        "media": "movie",
        "name": "Idiocracy",
        "year": 2006,
    },
    "Citizen Kane": {
        "id_imdb": "tt0033467",
        "id_tmdb": 15,
        "media": "movie",
        "name": "Citizen Kane",
        "year": 1941,
    },
    "Les Misérables": {
        "id_imdb": "tt10199590",
        "id_tmdb": 586863,
        "media": "movie",
        "name": "Les Misérables",
        "year": 2019,
    },
}

TEST_DATE = dt.date(2010, 12, 9)

RUSSIAN_LANG = Language.parse("ru")


class E2EResult(NamedTuple):
    code: int
    out: str


class MockRequestResponse:
    def __init__(self, status: int, content: str) -> None:
        self.status_code = status
        self.content = content

    def json(self) -> dict[str, Any]:
        from json import loads

        return loads(self.content)
