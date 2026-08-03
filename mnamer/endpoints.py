"""Provides a low-level interface for metadata media APIs."""

import datetime
import re
import xml.etree.ElementTree as ET
from re import match
from time import sleep

from mnamer.exceptions import (
    MnamerException,
    MnamerNetworkException,
    MnamerNotFoundException,
)
from mnamer.language import Language
from mnamer.utils import (
    clean_dict,
    parse_date,
    request_bytes,
    request_json,
    request_text,
)

OMDB_PLOT_TYPES = {"short", "long"}
MAX_RETRIES = 5
ANILIST_URL = "https://graphql.anilist.co"
ANIDB_URL = "http://api.anidb.net:9001/httpapi"
FANART_URL = "https://webservice.fanart.tv/v3.2"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

ANILIST_MEDIA_FIELDS = """
    id
    title { romaji english native userPreferred }
    description(asHtml: false)
    startDate { year month day }
    episodes
    externalLinks { site url }
"""


def _anilist_payload(query: str, variables: dict, cache: bool) -> dict:
    status, content = request_json(
        ANILIST_URL,
        body={"query": query, "variables": variables},
        headers={"accept": "application/json"},
        cache=cache,
    )
    if status == 404:
        raise MnamerNotFoundException
    if status != 200 or not isinstance(content, dict):  # pragma: no cover
        raise MnamerNetworkException("AniList down or unavailable?")
    if content.get("errors"):
        raise MnamerNetworkException("AniList returned an invalid response")
    return content


def anilist_media(
    id_anilist: str | int,
    cache: bool = True,
) -> dict:
    """Look up one anime by its AniList id."""
    try:
        media_id = int(id_anilist)
    except (TypeError, ValueError):
        raise MnamerException("id_anilist must be an integer") from None
    if media_id < 1:
        raise MnamerException("id_anilist must be greater than zero")
    query = f"""
    query ($id: Int!) {{
        Media(id: $id, type: ANIME) {{{ANILIST_MEDIA_FIELDS}
        }}
    }}
    """
    content = _anilist_payload(query, {"id": media_id}, cache)
    media = content.get("data", {}).get("Media")
    if not media:
        raise MnamerNotFoundException
    return media


def anilist_search(
    title: str,
    page: int = 1,
    per_page: int = 10,
    cache: bool = True,
) -> dict:
    """Search AniList anime entries by title."""
    if not title:
        raise MnamerException("title must be specified")
    if page < 1:
        raise MnamerException("page must be greater than zero")
    if per_page < 1 or per_page > 50:
        raise MnamerException("per_page must be between 1 and 50")
    query = f"""
    query ($search: String!, $page: Int!, $perPage: Int!) {{
        Page(page: $page, perPage: $perPage) {{
            pageInfo {{ currentPage hasNextPage lastPage }}
            media(search: $search, type: ANIME) {{{ANILIST_MEDIA_FIELDS}
            }}
        }}
    }}
    """
    content = _anilist_payload(
        query,
        {"search": title, "page": page, "perPage": per_page},
        cache,
    )
    page_data = content.get("data", {}).get("Page", {})
    if not page_data.get("media"):
        raise MnamerNotFoundException
    return page_data


def _anidb_title(titles: list[ET.Element], language: Language | None) -> str | None:
    preferred_languages = [language.a2] if language else []
    preferred_languages.extend(["en", "x-jat"])
    preferred_types = ("official", "main", "short", "synonym")
    for language_code in preferred_languages:
        for title_type in preferred_types:
            for title in titles:
                if title.attrib.get(XML_LANG) != language_code:
                    continue
                if title.attrib.get("type") == title_type and title.text:
                    return title.text.strip()
    return next((title.text.strip() for title in titles if title.text), None)


def _anidb_episode_number(value: str | None) -> int | None:
    result = re.search(r"\d+", value or "")
    return int(result.group()) if result else None


def anidb_anime(
    client: str,
    client_version: int,
    id_anidb: str | int,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """Retrieve and normalize an anime record from AniDB's HTTP XML API."""
    if not client:
        raise MnamerException("anidb client identifier must be specified")
    try:
        client_version = int(client_version)
        anime_id = int(id_anidb)
    except (TypeError, ValueError):
        raise MnamerException("AniDB client version and id must be integers") from None
    if client_version < 1 or anime_id < 1:
        raise MnamerException("AniDB client version and id must be greater than zero")
    status, content = request_text(
        ANIDB_URL,
        parameters={
            "request": "anime",
            "client": client.lower(),
            "clientver": client_version,
            "protover": 1,
            "aid": anime_id,
        },
        cache=cache,
    )
    if status == 404 or not content:
        raise MnamerNotFoundException
    if status != 200:  # pragma: no cover
        raise MnamerNetworkException("AniDB down or unavailable?")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:  # pragma: no cover
        raise MnamerNetworkException("AniDB returned invalid XML") from error
    if root.tag == "error" or root.tag != "anime":
        raise MnamerNotFoundException

    titles = list(root.findall("./titles/title"))
    episodes = []
    for episode in root.findall("./episodes/episode"):
        epno = episode.find("./epno")
        number = _anidb_episode_number(epno.text if epno is not None else None)
        if number is None:
            continue
        episode_titles = list(episode.findall("./title"))
        if not episode_titles:
            episode_titles = list(episode.findall("./titles/title"))
        airdate = episode.findtext("./airdate") or None
        episodes.append(
            {
                "id": episode.attrib.get("id"),
                "number": number,
                "type": epno.attrib.get("type", "1") if epno is not None else "1",
                "air_date": airdate,
                "title": _anidb_title(episode_titles, language),
            }
        )
    return {
        "id": root.attrib.get("id", str(anime_id)),
        "title": _anidb_title(titles, language),
        "start_date": root.findtext("./startdate") or None,
        "synopsis": root.findtext("./description") or None,
        "episodes": episodes,
    }


def fanart_images(
    api_key: str,
    media: str,
    media_id: str | int,
    cache: bool = True,
) -> dict:
    """Retrieve artwork metadata from Fanart.tv for a movie or TV series."""
    if not api_key:
        raise MnamerException("Fanart.tv API key must be specified")
    resources = {"movie": "movies", "episode": "tv"}
    if media not in resources:
        raise MnamerException("Fanart.tv media must be movie or episode")
    if not media_id:
        raise MnamerNotFoundException
    url = f"{FANART_URL}/{resources[media]}/{media_id}"
    status, content = request_json(
        url,
        headers={"api-key": api_key},
        cache=cache,
    )
    if status == 401:
        raise MnamerException("invalid Fanart.tv API key")
    if status == 404 or not content:
        raise MnamerNotFoundException
    if status != 200 or not isinstance(content, dict):  # pragma: no cover
        raise MnamerNetworkException("Fanart.tv down or unavailable?")
    return content


def fanart_image(url: str, cache: bool = True) -> bytes:
    """Download one artwork image from a URL returned by Fanart.tv."""
    status, content = request_bytes(url, cache=cache)
    if status != 200 or not content:  # pragma: no cover
        raise MnamerNetworkException("Fanart.tv image unavailable?")
    return content


def omdb_title(
    api_key: str,
    id_imdb: str | None = None,
    media: str | None = None,
    title: str | None = None,
    season: int | None = None,
    episode: int | None = None,
    year: int | None = None,
    plot: str | None = None,
    cache: bool = True,
) -> dict:
    """
    Looks up media by id using the Open Movie Database.

    Online docs: http://www.omdbapi.com/#parameters
    """
    if (not title and not id_imdb) or (title and id_imdb):
        raise MnamerException("either id_imdb or title must be specified")
    elif plot and plot not in OMDB_PLOT_TYPES:
        raise MnamerException(f"plot must be one of {','.join(OMDB_PLOT_TYPES)}")
    url = "http://www.omdbapi.com"
    parameters = {
        "apikey": api_key,
        "i": id_imdb,
        "t": title,
        "y": year,
        "season": season,
        "episode": episode,
        "type": media,
        "plot": plot,
    }
    parameters = clean_dict(parameters)
    status, content = request_json(url, parameters, cache=cache)
    error = content.get("Error") if isinstance(content, dict) else None
    if status == 401:
        if error == "Request limit reached!":
            raise MnamerException("API request limit reached")
        raise MnamerException("invalid API key")
    elif status != 200 or not isinstance(content, dict):  # pragma: no cover
        raise MnamerNetworkException("OMDb down or unavailable?")
    elif error:
        raise MnamerNotFoundException(error)
    return content


def omdb_search(
    api_key: str,
    query: str,
    year: int | None = None,
    media: str | None = None,
    page: int = 1,
    cache: bool = True,
) -> dict:
    """
    Search for media using the Open Movie Database.

    Online docs: http://www.omdbapi.com/#parameters.
    """
    if page < 1 or page > 100:
        raise MnamerException("page must be between 1 and 100")
    url = "http://www.omdbapi.com"
    parameters = {
        "apikey": api_key,
        "s": query,
        "y": year,
        "type": media,
        "page": page,
    }
    parameters = clean_dict(parameters)
    status, content = request_json(url, parameters, cache=cache)
    if status == 401:
        raise MnamerException("invalid API key")
    elif content and not content.get("totalResults"):
        raise MnamerNotFoundException()
    elif not content or status != 200:  # pragma: no cover
        raise MnamerNetworkException("OMDb down or unavailable?")
    return content


def tmdb_find(
    api_key: str,
    external_source: str,
    external_id: str,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """
    Search for The Movie Database objects using another DB's foreign key.

    Note: language codes aren't checked on this end or by TMDb, so if you
        enter an invalid language code your search itself will succeed, but
        certain fields like synopsis will just be empty.

    Online docs: developers.themoviedb.org/3/find.
    """
    sources = ["imdb_id", "freebase_mid", "freebase_id", "tvdb_id", "tvrage_id"]
    if external_source not in sources:
        raise MnamerException(f"external_source must be in {sources}")
    if external_source == "imdb_id" and not match(r"tt\d+", external_id):
        raise MnamerException("invalid imdb tt-const value")
    url = "https://api.themoviedb.org/3/find/" + external_id or ""
    parameters = {
        "api_key": api_key,
        "external_source": external_source,
        "language": language,
    }
    keys = [
        "movie_results",
        "person_results",
        "tv_episode_results",
        "tv_results",
        "tv_season_results",
    ]
    status, content = request_json(url, parameters, cache=cache)
    if status == 401:
        raise MnamerException("invalid API key")
    elif status != 200 or not any(content.keys()):  # pragma: no cover
        raise MnamerNetworkException("TMDb down or unavailable?")
    elif status == 404 or not any(content.get(k, {}) for k in keys):
        raise MnamerNotFoundException
    return content


def tmdb_movies(
    api_key: str,
    id_tmdb: str,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """
    Lookup a movie item using The Movie Database.

    Online docs: developers.themoviedb.org/3/movies.
    """
    url = f"https://api.themoviedb.org/3/movie/{id_tmdb}"
    parameters = {"api_key": api_key, "language": language}
    status, content = request_json(url, parameters, cache=cache)
    if status == 401:
        raise MnamerException("invalid API key")
    elif status == 404:
        raise MnamerNotFoundException
    elif status != 200 or not any(content.keys()):  # pragma: no cover
        raise MnamerNetworkException("TMDb down or unavailable?")
    return content


def tmdb_search_movies(
    api_key: str,
    title: str,
    year: int | str | None = None,
    language: Language | None = None,
    region: str | None = None,
    adult: bool = False,
    page: int = 1,
    cache: bool = True,
) -> dict:
    """
    Search for movies using The Movie Database.

    Online docs: developers.themoviedb.org/3/search/search-movies.
    """
    url = "https://api.themoviedb.org/3/search/movie"
    parameters = {
        "api_key": api_key,
        "query": title,
        "page": page,
        "include_adult": adult,
        "language": language,
        "region": region,
        "year": year,
    }
    status, content = request_json(url, parameters, cache=cache)
    if status == 401:
        raise MnamerException("invalid API key")
    elif status != 200 or not any(content.keys()):  # pragma: no cover
        raise MnamerNetworkException("TMDb down or unavailable?")
    elif status == 404 or status == 422 or not content.get("total_results"):
        raise MnamerNotFoundException
    return content


def tvdb_login(api_key: str | None) -> str:
    """
    Logs into TVDb using the provided api key.

    Note: You can register for a free TVDb key at thetvdb.com/?tab=apiregister
    Online docs: api.thetvdb.com/swagger#!/Authentication/post_login.
    """
    url = "https://api.thetvdb.com/login"
    body = {"apikey": api_key}
    status, content = request_json(url, body=body, cache=False)
    if status == 401:
        raise MnamerException("invalid api key")
    elif status != 200 or not content.get("token"):  # pragma: no cover
        raise MnamerNetworkException("TVDb down or unavailable?")
    return content["token"]


def tvdb_refresh_token(token: str) -> str:
    """
    Refreshes JWT token.

    Online docs: api.thetvdb.com/swagger#!/Authentication/get_refresh_token.
    """
    url = "https://api.thetvdb.com/refresh_token"
    headers = {"Authorization": f"Bearer {token}"}
    status, content = request_json(url, headers=headers, cache=False)
    if status == 401:
        raise MnamerException("invalid token")
    elif status != 200 or not content.get("token"):  # pragma: no cover
        raise MnamerNetworkException("TVDb down or unavailable?")
    return content["token"]


def tvdb_episodes_id(
    token: str,
    id_tvdb: str,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """
    Returns the full information for a given episode id.

    Online docs: https://api.thetvdb.com/swagger#!/Episodes.
    """
    Language.ensure_valid_for_tvdb(language)
    url = f"https://api.thetvdb.com/episodes/{id_tvdb}"
    headers = {"Authorization": f"Bearer {token}"}
    if language:
        headers["Accept-Language"] = language.a2
    status, content = request_json(
        url, headers=headers, cache=cache is True and language is None
    )
    if status == 401:
        raise MnamerException("invalid token")
    elif status == 404 or not content.get("data"):
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException("TVDb down or unavailable?")
    elif content["data"]["id"] == 0:
        raise MnamerNotFoundException
    return content


def tvdb_series_id(
    token: str,
    id_tvdb: str,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """
    Returns a series records that contains all information known about a
    particular series id.

    Online docs: api.thetvdb.com/swagger#!/Series/get_series_id.
    """
    Language.ensure_valid_for_tvdb(language)
    url = f"https://api.thetvdb.com/series/{id_tvdb}"
    headers = {"Authorization": f"Bearer {token}"}
    if language:
        headers["Accept-Language"] = language.a2
    status, content = request_json(
        url, headers=headers, cache=cache is True and language is None
    )
    if status == 401:
        raise MnamerException("invalid token")
    elif status == 404 or not content.get("data"):
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException("TVDb down or unavailable?")
    elif content["data"]["id"] == 0:
        raise MnamerNotFoundException
    return content


def tvdb_series_id_episodes(
    token: str,
    id_tvdb: str,
    page: int = 1,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """
    All episodes for a given series.

    Note: Paginated with 100 results per page.
    Online docs: api.thetvdb.com/swagger#!/Series/get_series_id_episodes.
    """
    Language.ensure_valid_for_tvdb(language)
    url = f"https://api.thetvdb.com/series/{id_tvdb}/episodes"
    headers = {"Authorization": f"Bearer {token}"}
    if language:
        headers["Accept-Language"] = language.a2
    parameters = {"page": page}
    status, content = request_json(
        url, parameters, headers=headers, cache=cache is True and language is None
    )
    if status == 401:
        raise MnamerException("invalid token")
    elif status == 404 or not content.get("data"):
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException("TVDb down or unavailable?")
    return content


def tvdb_series_id_episodes_query(
    token: str,
    id_tvdb: str,
    episode: int | None = None,
    season: int | None = None,
    page: int = 1,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """
    Allows the user to query against episodes for the given series.

    Note: Paginated with 100 results per page; omitted imdbId-- when would you
    ever need to query against both tvdb and imdb series ids?
    Online docs: api.thetvdb.com/swagger#!/Series/get_series_id_episodes_query.
    """
    Language.ensure_valid_for_tvdb(language)
    url = f"https://api.thetvdb.com/series/{id_tvdb}/episodes/query"
    headers = {"Authorization": f"Bearer {token}"}
    if language:
        headers["Accept-Language"] = language.a2
    parameters = {"airedSeason": season, "airedEpisode": episode, "page": page}
    status, content = request_json(
        url,
        parameters,
        headers=headers,
        cache=cache is True and language is None,
    )
    if status == 401:
        raise MnamerException("invalid token")
    elif status == 404 or not content.get("data"):
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException("TVDb down or unavailable?")
    return content


def tvdb_search_series(
    token: str,
    series: str | None = None,
    id_imdb: str | None = None,
    id_zap2it: str | None = None,
    language: Language | None = None,
    cache: bool = True,
) -> dict:
    """
    Allows the user to search for a series based on the following parameters.

    Online docs: https://api.thetvdb.com/swagger#!/Search/get_search_series
    Note: results a maximum of 100 entries per page, no option for pagination.
    """
    Language.ensure_valid_for_tvdb(language)
    url = "https://api.thetvdb.com/search/series"
    parameters = {"name": series, "imdbId": id_imdb, "zap2itId": id_zap2it}
    headers = {"Authorization": f"Bearer {token}"}
    if language:
        headers["Accept-Language"] = language.a2
    status, content = request_json(
        url, parameters, headers=headers, cache=cache is True and language is None
    )
    if status == 401:
        raise MnamerException("invalid token")
    elif status == 405:
        raise MnamerException(
            "series, id_imdb, id_zap2it parameters are mutually exclusive"
        )
    elif status == 404 or not content.get("data"):
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException("TVDb down or unavailable?")
    return content


def tvmaze_show(
    id_tvmaze: str,
    embed_episodes: bool = False,
    cache: bool = False,
    attempt: int = 1,
):
    """
    Retrieve all primary information for a given show.

    Online docs: https://www.tvmaze.com/api#show-main-information
    """
    url = f"http://api.tvmaze.com/shows/{id_tvmaze}"
    parameters = {}
    if embed_episodes:
        parameters["embed"] = "episodes"
    status, content = request_json(url, parameters, cache=cache)
    if status == 443 and attempt <= MAX_RETRIES:  # pragma: no cover
        sleep(attempt * 2)
        return tvmaze_show(id_tvmaze, embed_episodes, cache, attempt + 1)
    elif status == 404 or not content:
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException
    return content


def tvmaze_show_search(query: str, cache: bool = True, attempt: int = 1) -> dict:
    """
    Search through all the shows in the database by the show's name. A fuzzy
    algorithm is used (with a fuzziness value of 2), meaning that shows will be
    found even if your query contains small typos. Results are returned in order
    of relevancy (best matches on top) and contain each show's full information.

    Online docs: https://www.tvmaze.com/api#show-search
    """
    url = "http://api.tvmaze.com/search/shows"
    parameters = {"q": query}
    status, content = request_json(url, parameters, cache=cache)
    if status == 443 and attempt <= MAX_RETRIES:  # pragma: no cover
        sleep(attempt * 2)
        return tvmaze_show_search(query, cache, attempt + 1)
    elif status == 404 or not content:
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException
    return content


def tvmaze_show_single_search(query: str, cache: bool = True, attempt: int = 1) -> dict:
    """
    Singlesearch endpoint either returns exactly one result, or no result at
    all. This endpoint is also forgiving of typos, but less so than the regular
    search (with a fuzziness of 1 instead of 2), to reduce the chance of a false
    positive.

    Online docs: https://www.tvmaze.com/api#show-single-search
    """
    url = "http://api.tvmaze.com/singlesearch/shows"
    parameters = {"q": query}
    status, content = request_json(url, parameters, cache=cache)
    if status == 443 and attempt <= MAX_RETRIES:  # pragma: no cover
        sleep(attempt * 2)
        return tvmaze_show_single_search(query, cache, attempt + 1)
    elif status == 404 or not content:
        raise MnamerNotFoundException
    elif status != 200:  # pragma: no cover
        raise MnamerNetworkException
    return content


def tvmaze_show_lookup(
    id_imdb: str | None = None,
    id_tvdb: str | None = None,
    cache: bool = True,
    attempt: int = 1,
) -> dict:
    """
    If you already know a show's tvrage, thetvdb or IMDB ID, you can use this
    endpoint to find this exact show on TVmaze.

    Online docs: https://www.tvmaze.com/api#show-lookup
    """
    if not [id_imdb, id_tvdb].count(None) == 1:
        raise MnamerException("id_imdb and id_tvdb are mutually exclusive")
    url = "http://api.tvmaze.com/lookup/shows"
    parameters = {"imdb": id_imdb, "thetvdb": id_tvdb}
    status, content = request_json(url, parameters, cache=cache)
    if status == 443 and attempt <= MAX_RETRIES:  # pragma: no cover
        sleep(attempt * 2)
        return tvmaze_show_lookup(id_imdb, id_tvdb, cache, attempt + 1)
    elif status == 404:
        raise MnamerNotFoundException
    elif status != 200 or not content:  # pragma: no cover
        raise MnamerNetworkException
    return content


def tvmaze_show_episodes_list(
    id_tvmaze: str,
    include_specials: bool = False,
    cache: bool = True,
    attempt: int = 1,
) -> dict:
    """
    A complete list of episodes for the given show. Episodes are returned in
    their airing order, and include full episode information. By default,
    specials are not included in the list.

    Online docs: https://www.tvmaze.com/api#show-episode-list
    """
    url = f"http://api.tvmaze.com/shows/{id_tvmaze}/episodes"
    parameters = {"specials": int(include_specials)}
    status, content = request_json(url, parameters, cache=cache)
    if status == 443 and attempt <= MAX_RETRIES:  # pragma: no cover
        sleep(attempt * 2)
        return tvmaze_show_episodes_list(
            id_tvmaze, include_specials, cache, attempt + 1
        )
    elif status == 404:
        raise MnamerNotFoundException
    elif status != 200 or not content:  # pragma: no cover
        raise MnamerNetworkException
    return content


def tvmaze_episodes_by_date(
    id_tvmaze: str,
    air_date: datetime.date | str,
    cache: bool = True,
    attempt: int = 1,
) -> dict:
    """
    Retrieves all episodes from this show that have aired on a specific date.
    Useful for daily shows that don't adhere to a common season numbering.

    Online docs: https://www.tvmaze.com/api#episodes-by-date
    """
    url = f"http://api.tvmaze.com/shows/{id_tvmaze}/episodesbydate"
    parameters = {"date": parse_date(air_date)}
    status, content = request_json(url, parameters, cache=cache)
    if status == 443 and attempt <= MAX_RETRIES:  # pragma: no cover
        sleep(attempt * 2)
        return tvmaze_episodes_by_date(id_tvmaze, air_date, cache, attempt + 1)
    elif status == 404:
        raise MnamerNotFoundException
    elif status != 200 or not content:  # pragma: no cover
        raise MnamerNetworkException
    return content


def tvmaze_episode_by_number(
    id_tvmaze: str,
    season: int | None,
    episode: int | None,
    cache: bool = True,
    attempt: int = 1,
) -> dict:
    """
    Retrieve one specific episode from this show given its season number and
    episode number.

    Online docs: https://www.tvmaze.com/api#episode-by-number
    """
    url = f"http://api.tvmaze.com/shows/{id_tvmaze}/episodebynumber"
    parameters = {"season": season, "number": episode}
    status, content = request_json(url, parameters, cache=cache)
    if status == 443 and attempt <= MAX_RETRIES:  # pragma: no cover
        sleep(attempt * 2)
        return tvmaze_episode_by_number(id_tvmaze, season, episode, cache, attempt + 1)
    elif status == 404:
        raise MnamerNotFoundException
    elif status != 200 or not content:  # pragma: no cover
        raise MnamerNetworkException
    return content
