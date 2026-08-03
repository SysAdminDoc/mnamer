[![PyPI](https://img.shields.io/pypi/v/mnamer.svg?style=for-the-badge)](https://pypi.python.org/pypi/mnamer)
[![Tests](https://img.shields.io/github/actions/workflow/status/jkwill87/mnamer/.github/workflows/push.yml?branch=main&style=for-the-badge&label=Tests)](https://github.com/jkwill87/mnamer/actions/workflows/push.yml?query=branch:main)
[![Coverage](https://img.shields.io/codecov/c/github/jkwill87/mnamer/main.svg?style=for-the-badge)](https://codecov.io/gh/jkwill87/mnamer)
[![Licence](https://img.shields.io/github/license/jkwill87/mnamer.svg?style=for-the-badge)](https://en.wikipedia.org/wiki/MIT_License)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=for-the-badge)](https://github.com/astral-sh/ruff)

<img src="https://github.com/jkwill87/mnamer/raw/main/assets/logo.png" width="450"/>

# mnamer

mnamer (**m**edia re**namer**) is an intelligent and highly configurable media organization utility. It parses media filenames for metadata, searches the web to fill in the blanks, and then renames and moves them.

Currently it has integration support with [TVDb](https://thetvdb.com), [TvMaze](https://www.tvmaze.com), [AniDB](https://anidb.net), and [AniList](https://anilist.co) for television episodes, [TMDb](https://www.themoviedb.org/) and [OMDb](https://www.omdbapi.com) for movies, and [MusicBrainz](https://musicbrainz.org) for music and audiobook files.

<img src="https://github.com/jkwill87/mnamer/raw/main/assets/screenshot.png" width="750"/>

## Documentation

Check out the [wiki page](https://github.com/jkwill87/mnamer/wiki) for more details.

💾 [**Installation**](https://github.com/jkwill87/mnamer/wiki/Installation)

`$ uv tool install mnamer` or `$ pip3 install --user mnamer`

🤖 [**Automation**](https://github.com/jkwill87/mnamer/wiki/Automation)

`$ docker pull jkwill87/mnamer`

✍️ [**Formatting**](https://github.com/jkwill87/mnamer/wiki/Formatting)

Using the **episode-directory**, **episode-format**, **movie-directory**, **movie-format**, or **music-format** settings you customize how your files are renamed. Variables wrapped in braces `{}` get substituted with of parsed values of template field variables.

🌐 [**Internationalization**](https://github.com/jkwill87/mnamer/wiki/Internationalization)

Language is supported by the default TMDb and TVDb providers. You can use the `--language` setting to set the language used for templating.

mnamer also supports subtitle files (.srt, .idx, .sub). It will use the format pattern used for movie or episode media files with its extension prefixed by its 2-letter language code.

When a target has an adjacent `.nfo`, `.xml`, or `.json` sidecar, mnamer reads
local movie, episode, music-video, and provider-ID metadata before contacting an
online provider. This makes Jellyfin/Plex-compatible library exports
reproducible offline; the configured online provider remains the fallback when
no usable sidecar is available.

Online providers use a per-provider circuit breaker. Three consecutive network
failures open the circuit for 30 seconds so a batch fails fast while an API is
unavailable; a successful retry closes it again.

🧰 [**Settings**](https://github.com/jkwill87/mnamer/wiki/Settings)

```
USAGE: mnamer [preferences] [directives] target [targets ...]

POSITIONAL:
  [TARGET,...]: media file file path(s) to process

PARAMETERS:
  The following flags can be used to customize mnamer's behaviour. Their long
  forms may also be set in a '.mnamer-v2.json' config file, in which case cli
  arguments will take precedence.

  -b, --batch: process automatically without interactive prompts
  --artwork: download Fanart.tv poster, fanart, and logo files
  -l, --lower: rename files using lowercase characters
  -r, --recurse: search for files within nested directories
  -s, --scene: use dots in place of alphanumeric chars
  -v, --verbose: increase output verbosity
  --hits=<NUMBER>: limit the maximum number of hits for each query
  --ignore=<PATTERN,...>: ignore files matching these regular expressions
  --language=<LANG>: specify the search language
  --mask=<EXTENSION,...>: only process given file types
  --no-guess: disable best guess; e.g. when no matches or network down
  --no-overwrite: prevent relocation if it would overwrite a file
  --no-style: print to stdout without using colour or unicode chars
  --movie-api={*tmdb,omdb}: set movie api provider
  --movie-directory: set movie relocation directory
  --movie-format: set movie renaming format specification
  --episode-api={tvdb,*tvmaze,anidb,anilist}: set episode api provider
  --episode-directory: set episode relocation directory
  --episode-format: set episode renaming format specification
  --music-api={*musicbrainz}: set music api provider
  --music-directory: set music relocation directory
  --music-format: set music renaming format specification

DIRECTIVES:
  Directives are one-off arguments that are used to perform secondary tasks
  like overriding media detection. They can't be used in '.mnamer-v2.json'.

  -V, --version: display the running mnamer version number
  --clear-cache: clear request cache
  --config-dump: prints current config JSON to stdout then exits
  --config-ignore: skips loading config file for session
  --config-path=<PATH>: specifies configuration path to load
  --id-imdb=<ID>: specify an IMDb movie id override
  --id-tmdb=<ID>: specify a TMDb movie id override
  --id-tvdb=<ID>: specify a TVDb series id override
  --id-tvmaze=<ID>: specify a TvMaze series id override
  --id-anidb=<ID>: specify an AniDB anime id override
  --id-anilist=<ID>: specify an AniList anime id override
  --id-musicbrainz=<ID>: specify a MusicBrainz recording id override
  --no-cache: disable request cache
  --media={movie,episode,music}: override media detection
  --test: mocks the renaming and moving of files
```

Parameters can either by entered as command line arguments or from a config file named `.mnamer-v2.json`.

### Anime providers

AniList can search anime titles without credentials:

`$ mnamer --episode-api=anilist "One Piece - E1000.mkv"`

AniDB supplies episode titles and air dates. Its HTTP API requires a registered
client identifier and version, provided through `API_KEY_ANIDB` and
`API_VERSION_ANIDB` (or `api_key_anidb` in `.mnamer-v2.json`). Use
`--id-anidb=<ID>` when a filename needs an exact AniDB anime record. AniDB title
searches use AniList's cross-provider links to find the AniDB id, then retrieve
the episode data from AniDB.

Artwork downloading is opt-in. Set `API_KEY_FANART` (or `api_key_fanart` in the
configuration file) and pass `--artwork`; artwork is written as `poster`,
`fanart`, and `logo` beside the renamed media when Fanart.tv has a matching
TMDb/IMDb movie id or TVDb series id.

### MusicBrainz provider

Common music containers (`.aac`, `.flac`, `.m4a`, `.m4b`, `.mp3`, `.ogg`,
`.opus`, and `.wav`) are detected as music automatically. The default
MusicBrainz format is `{artist} - {album} - {track:02} - {title}.{extension}`;
use `--music-api=musicbrainz` or `--media=music` when a filename needs an
explicit override. MusicBrainz does not require an API key; requests identify
mnamer with a descriptive User-Agent.

## Contributions

Community contributions are a welcome addition to the project. In order to be merged upstream any additions will need to be formatted with [ruff](https://docs.astral.sh/ruff/) for consistency with the rest of the project and pass the continuous integration tests run against each PR. Before introducing any major features or changes to the configuration api please consider opening [an issue](https://github.com/jkwill87/mnamer/issues) to outline your proposal.

Bug reports are also welcome on the [issue page](https://github.com/jkwill87/mnamer/issues). Please include any generated crash reports if applicable. Feature requests are welcome but consider checking out [if it is in the works](https://github.com/jkwill87/mnamer/issues?q=label%3Arequest) first to avoid duplication.
