from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from os import environ, path
from pathlib import Path
from shutil import move
from typing import Any, ClassVar
from urllib.parse import urlparse

from guessit import guessit  # type: ignore

from mnamer.const import MUSIC_CONTAINERS
from mnamer.endpoints import fanart_image, fanart_images
from mnamer.exceptions import MnamerException
from mnamer.language import Language
from mnamer.metadata import Metadata, MetadataEpisode, MetadataMovie, MetadataMusic
from mnamer.providers import LocalNfo, Provider
from mnamer.setting_store import SettingStore
from mnamer.subtitles import detect_subtitle_language
from mnamer.types import MediaType, ProviderType
from mnamer.utils import (
    crawl_in,
    filename_replace,
    filter_blacklist,
    filter_containers,
    is_subtitle,
    str_replace,
    str_sanitize,
    str_scenify,
)


class Target:
    """Manages metadata state for a media file and facilitates its relocation."""

    _providers: ClassVar[dict[ProviderType, Provider]] = {}

    _settings: SettingStore
    _provider: Provider
    _has_moved: bool
    _has_renamed: bool
    artwork_error: str | None
    artwork_downloaded: list[Path]
    _raw_metadata: dict[str, str]
    _parsed_metadata: Metadata

    source: Path
    metadata: Metadata

    def __init__(self, file_path: Path, settings: SettingStore | None = None):
        self.source = file_path
        self._settings = settings or SettingStore()
        self._has_moved = False
        self._has_renamed = False
        self.artwork_error = None
        self.artwork_downloaded = []
        self._parse(file_path)
        self._replace_before()
        self._override_metadata_ids()
        self._register_provider()

    def __str__(self) -> str:
        if isinstance(self.source, Path):
            return str(self.source.resolve())
        else:
            return str(self.source)

    @classmethod
    def populate_paths(cls: type[Target], settings: SettingStore) -> list[Target]:
        """Creates a list of Target objects for media files found in paths."""
        file_paths = crawl_in(settings.targets, settings.recurse)
        file_paths = filter_blacklist(file_paths, settings.ignore)
        file_paths = filter_containers(file_paths, settings.mask)
        targets = [cls(file_path, settings) for file_path in file_paths]
        targets = list(dict.fromkeys(targets))  # unique values
        targets = list(filter(cls._matches_media, targets))
        return targets

    @classmethod
    def reset_providers(cls):
        cls._providers.clear()

    @staticmethod
    def _matches_media(target: Target) -> bool:
        if not target._settings.media:
            return True
        else:
            return target._settings.media is target.metadata.to_media_type()

    @property
    def provider_type(self) -> ProviderType:
        provider_type = self._settings.api_for(self.metadata.to_media_type())
        assert provider_type
        return provider_type

    @property
    def directory(self) -> Path | None:
        settings_key = f"{self.metadata.to_media_type().value}_directory"
        directory = getattr(self._settings, settings_key)
        return Path(directory) if directory else None

    @property
    def destination(self) -> Path:
        """
        The destination Path for the target based on its metadata and user
        preferences.
        """
        if self.directory:
            dir_head_ = format(self.metadata, str(self.directory))
            dir_head_ = str_sanitize(dir_head_)
            dir_head = Path(dir_head_)
        else:
            dir_head = self.source.parent
        file_path = format(self.metadata, self._settings.formatting_for(self.metadata))
        dir_tail, filename = path.split(Path(file_path))
        filename = filename_replace(filename, self._settings.replace_after)
        if self._settings.scene:
            filename = str_scenify(filename)
        if self._settings.lower:
            filename = filename.lower()
        filename = str_sanitize(filename)
        directory = Path(dir_head, dir_tail)
        return Path(directory, filename)

    def _parse(self, file_path: Path):
        path_data: dict[str, Any] = {"language": self._settings.language}
        if is_subtitle(self.source):
            try:
                path_data["language"] = Language.parse(self.source.stem[-2:])
                file_path = Path(self.source.parent, self.source.stem[:-2])
            except MnamerException:
                pass
        media_override = getattr(self._settings.media, "value", self._settings.media)
        options = {"type": media_override, "language": path_data["language"]}
        raw_data = dict(guessit(str(file_path), options))
        if (
            not self._settings.media
            and file_path.suffix.lower() in MUSIC_CONTAINERS
        ):
            options = {**options, "type": MediaType.MUSIC.value}
            raw_data = dict(guessit(str(file_path), options))
        if isinstance(raw_data.get("season"), list):
            raw_data = dict(guessit(str(file_path.parts[-1]), options))
        for k, v in raw_data.items():
            if hasattr(v, "alpha3"):
                try:
                    path_data[k] = Language.parse(v)
                except MnamerException:
                    continue
            elif isinstance(v, int | str | dt.date):
                path_data[k] = v
            elif isinstance(v, list) and all(isinstance(_, int | str) for _ in v):
                path_data[k] = (
                    v
                    if k == "alternative_title"
                    and raw_data.get("type") == MediaType.MUSIC.value
                    or k == "episode"
                    and raw_data.get("type") == MediaType.EPISODE.value
                    else v[0]
                )
        if self._settings.media:
            media_type = self._settings.media
        elif path_data.get("type"):
            media_type = MediaType(path_data["type"])
        else:
            media_type = None
        meta_cls = {
            MediaType.EPISODE: MetadataEpisode,
            MediaType.MOVIE: MetadataMovie,
            MediaType.MUSIC: MetadataMusic,
            None: Metadata,
        }[media_type]
        self.metadata = meta_cls()
        self.metadata.quality = (
            " ".join(
                path_data[key]
                for key in path_data
                if key
                in (
                    "audio_codec",
                    "audio_profile",
                    "screen_size",
                    "source",
                    "video_codec",
                    "video_profile",
                )
            )
            or None
        )
        self.metadata.language = path_data.get("language")
        self.metadata.group = path_data.get("release_group")
        self.metadata.container = file_path.suffix or None
        if not self.metadata.language:
            try:
                self.metadata.language = path_data.get("language")
            except MnamerException:
                pass
        try:
            self.metadata.language_sub = path_data.get("subtitle_language")
        except MnamerException:
            pass
        if not self.metadata.language_sub:
            self.metadata.language_sub = detect_subtitle_language(self.source)
        if isinstance(self.metadata, MetadataMovie):
            self.metadata.name = path_data.get("title")
            self.metadata.year = path_data.get("year")
        elif isinstance(self.metadata, MetadataEpisode):
            self.metadata.date = path_data.get("date")
            episodes = path_data.get("episode")
            if isinstance(episodes, list):
                self.metadata.episodes = episodes
                self.metadata.episode = episodes[0] if episodes else None
            else:
                self.metadata.episode = episodes
            self.metadata.season = path_data.get("season")
            self.metadata.series = path_data.get("title")
            alternative_title = path_data.get("alternative_title")
            if alternative_title:
                self.metadata.series = f"{self.metadata.series} {alternative_title}"
            # adding year to title can reduce false positives
            # year = path_data.get("year")
            # if year:
            #     self.metadata.series = f"{self.metadata.series} {year}"
        elif isinstance(self.metadata, MetadataMusic):
            alternatives = path_data.get("alternative_title")
            if isinstance(alternatives, list):
                self.metadata.album = alternatives[0] if len(alternatives) > 1 else None
                self.metadata.title = alternatives[-1] if alternatives else None
            else:
                self.metadata.title = alternatives or path_data.get("episode_title")
            self.metadata.artist = path_data.get("artist") or path_data.get("title")
            self.metadata.track = path_data.get("track") or path_data.get("episode")
            self.metadata.year = path_data.get("year")

    def _override_metadata_ids(self):
        id_types = {
            "anidb",
            "anilist",
            "imdb",
            "musicbrainz",
            "tmdb",
            "tvdb",
            "tvmaze",
        }
        for id_type in id_types:
            attr = f"id_{id_type}"
            if not hasattr(self.metadata, attr):
                continue  # ensure metadata subclass supports id type
            value = getattr(self._settings, attr, None)
            if not value:
                continue  # apply override if set in directives
            setattr(self.metadata, attr, value)

    def _register_provider(self) -> None:
        provider_type = self.provider_type
        if provider_type and provider_type not in self._providers:
            self._providers[provider_type] = Provider.provider_factory(
                provider_type, self._settings
            )
        self._provider = self._providers[provider_type]

    def _replace_before(self) -> None:
        if not self._settings.replace_before:
            return
        for attr, value in vars(self.metadata).items():
            if not isinstance(value, str):
                continue
            if attr.startswith("_"):
                continue
            value = str_replace(value, self._settings.replace_before)
            setattr(self.metadata, attr, value)

    def query(self) -> list[Metadata]:
        """Queries the target's respective media provider for metadata."""
        results: Iterator[Metadata]
        try:
            results = iter([next(LocalNfo(self.source).search(self.metadata))])
        except MnamerException:
            results = self._provider.search(self.metadata)
        seen = set()
        response = []
        for idx, result in enumerate(results, start=1):
            if str(result) in seen:
                continue
            response.append(result)
            seen.add(str(result))
            if idx >= self._settings.hits:
                break
        return response

    def relocate(self) -> None:
        """Performs the action of renaming and/or moving a file."""
        destination_path = Path(self.destination).resolve()
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        artwork = self._prepare_artwork(destination_path.parent)
        try:
            move(str(self.source), destination_path)
        except OSError as e:  # pragma: no cover
            raise MnamerException from e
        self._write_artwork(artwork)

    @staticmethod
    def _artwork_sources(media_type: MediaType) -> dict[str, tuple[str, ...]]:
        if media_type is MediaType.MOVIE:
            return {
                "poster": ("movieposter",),
                "fanart": ("moviebackground",),
                "logo": ("hdmovielogo", "movielogo"),
            }
        return {
            "poster": ("tvposter",),
            "fanart": ("showbackground", "tvbackground"),
            "logo": ("hdtvlogo", "clearlogo"),
        }

    def _artwork_id(self) -> str | None:
        if isinstance(self.metadata, MetadataMovie):
            return str(self.metadata.id_tmdb or self.metadata.id_imdb or "") or None
        if isinstance(self.metadata, MetadataEpisode):
            return str(self.metadata.id_tvdb or "") or None
        return None

    def _select_artwork(self, images: list[dict]) -> dict | None:
        if not images:
            return None
        language = self.metadata.language.a2 if self.metadata.language else None

        def rank(image: dict) -> tuple[int, int]:
            image_language = image.get("lang")
            language_rank = (
                3
                if language and image_language == language
                else 2
                if image_language == "en"
                else 1
                if image_language == "00"
                else 0
            )
            try:
                likes = int(image.get("likes", 0))
            except (TypeError, ValueError):
                likes = 0
            return language_rank, likes

        return max(images, key=rank)

    def _prepare_artwork(self, directory: Path) -> list[tuple[Path, bytes]]:
        if not self._settings.artwork:
            return []
        api_key = self._settings.api_key_fanart or environ.get("API_KEY_FANART")
        artwork_id = self._artwork_id()
        if not artwork_id:
            return []
        try:
            response = fanart_images(
                api_key or "",
                self.metadata.to_media_type().value,
                artwork_id,
                cache=not self._settings.no_cache,
            )
        except MnamerException as error:
            self.artwork_error = str(error)
            return []
        prepared = []
        for name, categories in self._artwork_sources(
            self.metadata.to_media_type()
        ).items():
            entry = next(
                (
                    selected
                    for category in categories
                    for selected in [
                        self._select_artwork(response.get(category, []))
                    ]
                    if selected
                ),
                None,
            )
            if not entry or not entry.get("url"):
                continue
            suffix = Path(urlparse(entry["url"]).path).suffix.lower()
            if suffix not in {".jpeg", ".jpg", ".png", ".webp"}:
                suffix = ".jpg"
            destination = directory / f"{name}{suffix}"
            if destination.exists():
                continue
            try:
                content = fanart_image(
                    entry["url"],
                    cache=not self._settings.no_cache,
                )
            except MnamerException as error:
                self.artwork_error = str(error)
                continue
            prepared.append((destination, content))
        return prepared

    def _write_artwork(self, artwork: list[tuple[Path, bytes]]) -> None:
        for destination, content in artwork:
            try:
                destination.write_bytes(content)
            except OSError as error:  # pragma: no cover
                self.artwork_error = str(error)
            else:
                self.artwork_downloaded.append(destination)
