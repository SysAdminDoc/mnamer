"""Local sidecar metadata readers for common media-library formats."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from mnamer.metadata import Metadata, MetadataEpisode, MetadataMovie, MetadataMusic
from mnamer.types import MediaType
from mnamer.utils import parse_date, year_parse


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _value(data: dict[str, Any], *names: str) -> Any:
    normalized = {_key(str(name)): value for name, value in data.items()}
    for name in names:
        value = normalized.get(_key(name))
        if value not in (None, "", [], {}):
            return value
    return None


def _has_value(data: dict[str, Any], *names: str) -> bool:
    return _value(data, *names) is not None


def _xml_data(element: ET.Element) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name, value in element.attrib.items():
        data[_key(name)] = value
    for child in element.iter():
        child_key = _key(child.tag.rsplit("}", 1)[-1])
        value = (child.text or "").strip()
        if value and child is not element:
            data[child_key] = value
        if child_key == "uniqueid" and value:
            id_type = child.attrib.get("type")
            if id_type:
                data[f"{_key(id_type)}id"] = value
        if child_key == "guid":
            guid = child.attrib.get("id") or child.attrib.get("value")
            if guid:
                data["guid"] = guid
    return data


def _json_record(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return next((item for item in payload if isinstance(item, dict)), {})
    if not isinstance(payload, dict):
        return {}

    for container_name in ("MediaContainer", "metadata", "data", "item"):
        container = _value(payload, container_name)
        if isinstance(container, list):
            return _json_record(container)
        if isinstance(container, dict):
            nested = _json_record(container)
            if nested:
                return nested
            return container

    for collection_name in ("Metadata", "items", "results"):
        collection = _value(payload, collection_name)
        if isinstance(collection, list):
            return _json_record(collection)
    return payload


def _json_data(payload: Any) -> dict[str, Any]:
    record = _json_record(payload)
    data = dict(record)
    provider_ids = _value(record, "providerIds", "provider_ids")
    if isinstance(provider_ids, dict):
        for name, value in provider_ids.items():
            if value in (None, ""):
                continue
            provider_key = _key(str(name))
            data[provider_key] = value
            data[f"{provider_key}id"] = value
    return data


def _xml_record(path: Path, media_type: MediaType) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    accepted = {
        MediaType.MOVIE: {"movie", "film", "video"},
        MediaType.EPISODE: {"episode", "episodedetails", "tvshow", "video"},
        MediaType.MUSIC: {"musicvideo", "track", "song", "recording", "audio"},
    }[media_type]
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag in accepted:
            return _xml_data(element)
    return _xml_data(root)


def _load_data(path: Path, media_type: MediaType) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return _json_data(json.loads(path.read_text(encoding="utf-8")))
    return _xml_record(path, media_type)


def _year(value: Any) -> int | None:
    return year_parse(str(value)) if value not in (None, "") else None


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _date(value: Any):
    if value in (None, ""):
        return None
    try:
        return parse_date(str(value))
    except (TypeError, ValueError):
        return None


def _common(query: Metadata) -> dict[str, Any]:
    return {
        "container": query.container,
        "group": query.group,
        "language": query.language,
        "language_sub": query.language_sub,
        "quality": query.quality,
    }


def _movie(data: dict[str, Any], query: MetadataMovie) -> MetadataMovie | None:
    if not _has_value(
        data,
        "title",
        "name",
        "originaltitle",
        "year",
        "premiered",
        "releasedate",
        "imdbid",
        "tmdbid",
        "uniqueid",
    ):
        return None
    year_value = _value(data, "year", "premiered", "releasedate")
    return MetadataMovie(
        **_common(query),
        name=_value(data, "title", "name", "originaltitle") or query.name,
        year=str(year_value) if year_value is not None else query.year,
        synopsis=_value(data, "plot", "overview", "outline") or query.synopsis,
        id_imdb=_value(data, "imdbid", "imdb") or query.id_imdb,
        id_tmdb=_value(data, "tmdbid", "tmdb") or query.id_tmdb,
    )


def _episode(data: dict[str, Any], query: MetadataEpisode) -> MetadataEpisode | None:
    if not _has_value(
        data,
        "title",
        "showtitle",
        "seriesname",
        "series",
        "season",
        "episode",
        "aired",
        "premiered",
        "tvdbid",
        "tvmazeid",
    ):
        return None
    season = _integer(
        _value(
            data,
            "season",
            "seasonnumber",
            "parentindexnumber",
            "parentindex",
        )
    )
    episode = _integer(
        _value(data, "episode", "episodenumber", "indexnumber", "index")
    )
    return MetadataEpisode(
        **_common(query),
        series=_value(
            data,
            "showtitle",
            "seriesname",
            "series",
            "tvshowtitle",
            "grandparenttitle",
        )
        or query.series,
        season=season if season is not None else query.season,
        episode=episode if episode is not None else query.episode,
        date=_date(_value(data, "aired", "premiered", "premieredate")) or query.date,
        title=_value(data, "title", "name") or query.title,
        synopsis=_value(data, "plot", "overview", "outline") or query.synopsis,
        id_anidb=_value(data, "anidbid", "anidb") or query.id_anidb,
        id_anilist=_value(data, "anilistid", "anilist") or query.id_anilist,
        id_tvdb=_value(data, "tvdbid", "tvdb") or query.id_tvdb,
        id_tvmaze=_value(data, "tvmazeid", "tvmaze") or query.id_tvmaze,
    )


def _music(data: dict[str, Any], query: MetadataMusic) -> MetadataMusic | None:
    if not _has_value(
        data,
        "title",
        "name",
        "artist",
        "album",
        "track",
        "tracknumber",
        "musicbrainzid",
        "musicbrainztrackid",
    ):
        return None
    return MetadataMusic(
        **_common(query),
        artist=_value(data, "artist", "albumartist") or query.artist,
        album=_value(data, "album", "release") or query.album,
        track=_integer(_value(data, "track", "tracknumber", "indexnumber"))
        or query.track,
        title=_value(data, "title", "name") or query.title,
        year=_year(
            _value(data, "year", "date", "releasedate", "premieredate")
        )
        or query.year,
        id_musicbrainz=_value(
            data,
            "musicbrainzid",
            "musicbrainztrackid",
            "musicbrainzrecordingid",
        )
        or query.id_musicbrainz,
    )


def _metadata(data: dict[str, Any], query: Metadata) -> Metadata | None:
    if isinstance(query, MetadataMovie):
        return _movie(data, query)
    if isinstance(query, MetadataEpisode):
        return _episode(data, query)
    if isinstance(query, MetadataMusic):
        return _music(data, query)
    return None


def _sidecars(source: Path, media_type: MediaType) -> list[Path]:
    candidates: list[Path] = []
    if source.name:
        if source.suffix:
            candidates.extend(source.with_suffix(suffix) for suffix in (".nfo", ".xml", ".json"))
        candidates.extend(
            source.parent / name
            for name in {
                MediaType.MOVIE: ("movie.nfo", "metadata.nfo", "metadata.xml", "metadata.json"),
                MediaType.EPISODE: ("tvshow.nfo", "metadata.nfo", "metadata.xml", "metadata.json"),
                MediaType.MUSIC: ("musicvideo.nfo", "metadata.nfo", "metadata.xml", "metadata.json"),
            }[media_type]
        )
    return list(dict.fromkeys(path for path in candidates if path.is_file()))


def read_nfo(source: Path, query: Metadata) -> Metadata | None:
    """Read the first usable local metadata sidecar for a target."""
    media_type = query.to_media_type()
    for path in _sidecars(source, media_type):
        try:
            data = _load_data(path, media_type)
        except (OSError, ET.ParseError, json.JSONDecodeError, UnicodeError):
            continue
        metadata = _metadata(data, query)
        if metadata:
            return metadata
    return None
