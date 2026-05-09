"""Shared constant definitions."""

import datetime as dt
from pathlib import Path
from platform import platform, python_version
from sys import argv, gettrace, version_info


def _resolve_version() -> str:
    try:
        from mnamer.__version__ import __version__

        return __version__
    except ModuleNotFoundError:
        from setuptools_scm import get_version  # type: ignore[import-untyped]

        return get_version(root="..", relative_to=__file__, local_scheme="dirty-tag")


def _resolve_appdirs_version() -> str:
    try:
        from appdirs import __version__  # type: ignore[import-untyped]

        return __version__
    except ModuleNotFoundError:
        return "N/A"


def _resolve_cache_dir() -> str:
    try:
        from appdirs import user_cache_dir  # type: ignore[import-untyped]

        return user_cache_dir()
    except ModuleNotFoundError:
        return "N/A"


def _resolve_guessit_version() -> str:
    try:
        from guessit import __version__  # type: ignore[import-untyped]

        return __version__
    except ModuleNotFoundError:
        return "N/A"


def _resolve_requests_version() -> str:
    try:
        from requests import __version__

        return __version__
    except ModuleNotFoundError:
        return "N/A"


def _resolve_requests_cache_version() -> str:
    try:
        from requests_cache import __version__

        return __version__
    except ModuleNotFoundError:
        return "N/A"


def _resolve_teletype_version() -> str:
    try:
        from teletype import VERSION

        return VERSION
    except ModuleNotFoundError:
        return "N/A"


VERSION: str = _resolve_version()
appdirs_version: str = _resolve_appdirs_version()
cache_dir: str = _resolve_cache_dir()
guessit_version: str = _resolve_guessit_version()
requests_version: str = _resolve_requests_version()
requests_cache_version: str = _resolve_requests_cache_version()
teletype_version: str = _resolve_teletype_version()


CACHE_PATH = Path(
    cache_dir, f"mnamer-py{version_info.major}.{version_info.minor}"
).absolute()

CURRENT_YEAR = dt.datetime.now().year

DEPRECATED = {"no_replace", "replacements"}

IS_DEBUG = gettrace() is not None

SUBTITLE_CONTAINERS = [".srt", ".idx", ".sub"]


SYSTEM = {
    "date": dt.date.today(),
    "platform": platform(),
    "arguments": argv[1:],
    "cache location": f"{CACHE_PATH}.sqlite",
    "python version": python_version(),
    "mnamer version": VERSION,
    "appdirs version": appdirs_version,
    "guessit version": guessit_version,
    "requests version": requests_version,
    "requests cache version": requests_cache_version,
    "teletype version": teletype_version,
}

USAGE = "USAGE: mnamer [preferences] [directives] target [targets ...]"
