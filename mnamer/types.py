"""Enum type definitions."""

from __future__ import annotations

from enum import Enum


class MediaType(Enum):
    EPISODE = "episode"
    MOVIE = "movie"
    MUSIC = "music"

    @classmethod
    def to_media_type(cls) -> type[MediaType]:
        return cls


class MessageType(Enum):
    INFO = None
    ALERT = "yellow"
    ERROR = "red"
    SUCCESS = "green"
    HEADING = "bold"


class ProviderType(Enum):
    TVDB = "tvdb"
    TVMAZE = "tvmaze"
    ANIDB = "anidb"
    ANILIST = "anilist"
    MUSICBRAINZ = "musicbrainz"
    TMDB = "tmdb"
    OMDB = "omdb"


class SettingType(Enum):
    DIRECTIVE = "directive"
    PARAMETER = "parameter"
    POSITIONAL = "positional"
    CONFIGURATION = "configuration"
