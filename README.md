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

The image targets both `linux/amd64` and `linux/arm64`, runs as the unprivileged
`mnamer` user, and exposes `/config` and `/mnt` as volumes. Mount a directory
containing `.mnamer-v2.toml` at `/config` and the media directory at `/mnt`:

```console
$ docker run --rm \
    --mount type=bind,src=/path/to/mnamer-config,dst=/config \
    --mount type=bind,src=/path/to/media,dst=/mnt \
    jkwill87/mnamer --batch /mnt
```

Build and publish both architectures with Docker Buildx:

```console
$ docker buildx build --platform linux/amd64,linux/arm64 \
    --tag jkwill87/mnamer:latest --push .
```

The default container UID and GID are both `1000`; rebuild with `--build-arg
UID=... --build-arg GID=...` when the NAS volume requires a different owner.

✍️ [**Formatting**](https://github.com/jkwill87/mnamer/wiki/Formatting)

Using the **episode-directory**, **episode-format**, **movie-directory**, **movie-format**, or **music-format** settings you customize how your files are renamed. Variables wrapped in braces `{}` get substituted with of parsed values of template field variables.

🌐 [**Internationalization**](https://github.com/jkwill87/mnamer/wiki/Internationalization)

Language is supported by the default TMDb and TVDb providers. You can use the `--language` setting to set the language used for templating.

mnamer also supports subtitle files (.srt, .idx, .sub). It will use the format pattern used for movie or episode media files with its extension prefixed by its 2-letter language code. When a subtitle filename has no language code, dialogue in text-based `.srt` and `.sub` files is detected conservatively; ambiguous or unsupported files still use the normal prompt or batch skip behavior.

For mangled releases, install the optional smart-match extra with `pip install
"mnamer[smart-match]"` and pass `--smart-match`. It uses the
`all-MiniLM-L6-v2` embedding model to rerank provider results and downloads the
model on first use.

Video targets also expose `{hdr}` and `{audio}` template values. HDR10, HDR10+,
Dolby Vision, HLG, and Atmos tags are read from release names; when a tag is
absent, an installed `ffprobe` is queried briefly for stream metadata.

For an interactive batch preview with per-file accept/reject and inline metadata
editing, install `pip install "mnamer[tui]"` and run `mnamer --tui TARGET...`.

For Radarr/Sonarr-style ingestion folders, install `pip install "mnamer[watch]"`
and run `mnamer --watch --batch --recurse /downloads/complete`. Watch mode
processes matching files already in the folder, then waits for new files to
finish copying before processing them. Use `--no-overwrite` when the destination
library must remain untouched.

When a target has an adjacent `.nfo`, `.xml`, or `.json` sidecar, mnamer reads
local movie, episode, music-video, and provider-ID metadata before contacting an
online provider. This makes Jellyfin/Plex-compatible library exports
reproducible offline; the configured online provider remains the fallback when
no usable sidecar is available.

Online providers use a per-provider circuit breaker. Three consecutive network
failures open the circuit for 30 seconds so a batch fails fast while an API is
unavailable; a successful retry closes it again.

Movie title searches include the parsed release year plus the adjacent years,
which covers releases whose filesystem year differs from the catalog year at a
December boundary.

Episode packs such as `S01E01E02`, `S01E01-E02`, and lowercase `e01-e02` retain
all detected episode numbers. The first episode remains the lookup key for
existing providers, and `{episode_range}` is available in episode formats for
pack-aware naming.

🧰 [**Settings**](https://github.com/jkwill87/mnamer/wiki/Settings)

```
USAGE: mnamer [preferences] [directives] target [targets ...]

POSITIONAL:
  [TARGET,...]: media file file path(s) to process

PARAMETERS:
  The following flags can be used to customize mnamer's behaviour. Their long
  forms may also be set in a '.mnamer-v2.toml' config file, in which case cli
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
  --preset={trash}: apply a built-in naming preset
  --smart-match: rerank title matches with sentence embeddings
  --thumbnails: generate a burned-in JPEG beside moved media
  --thumbnail-width=<PIXELS>: set generated thumbnail width
  --tui: preview, edit, accept, or reject files in a Textual UI
  --serve: run the remote preview web UI
  --serve-host=<HOST>: bind the web UI to this host
  --serve-port=<PORT>: bind the web UI to this TCP port
  --watch: continuously process new files in target folders
  --on-success=<CMD>: run a command after each successful move
  --dry-run-diff: print a unified source-to-destination plan
  --log-format={*text,json}: choose text or JSON log output

DIRECTIVES:
  Directives are one-off arguments that are used to perform secondary tasks
  like overriding media detection. They can't be used in '.mnamer-v2.toml'.

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
  --undo: replay the last session's recorded moves
```

Parameters can either be entered as command line arguments or from a TOML
config file named `.mnamer-v2.toml`. TOML comments and trailing commas are
supported. Existing `.mnamer-v2.json` files remain readable as a compatibility
fallback; pass `--config-path` to select either format explicitly.

Every successful relocation is recorded in a rotating cache journal. Run
`mnamer --undo` to replay the most recent session in reverse order. Undo skips
missing destinations and existing sources rather than overwriting user changes.

Use `--on-success` to invoke a post-action command after a real relocation.
Commands are executed as argument lists without an implicit shell. The hook
receives `MNAMER_SOURCE_PATH`, `MNAMER_TARGET_PATH`, `MNAMER_MEDIA_TYPE`, and
any available `MNAMER_ID_*` metadata variables. A hook failure is reported but
does not roll back a completed move.

Use `mnamer --batch --dry-run-diff TARGET...` to review the planned relocations
without changing files. Each candidate is printed as a standard unified diff;
the same matching, overwrite, and subtitle checks as a real run still apply.

Pass `--thumbnails` to extract a representative frame with ffmpeg, resize it
to 640 pixels wide by default, and burn the matched title into a JPEG beside
each relocated movie or episode. Set `--thumbnail-width` to change the width.
Thumbnail generation is optional and non-fatal; if ffmpeg is unavailable the
media move still completes and mnamer reports the reason.

Use `--preset trash` to apply the available-field equivalent of the [TRaSH
Guides naming scheme](https://trash-guides.info/Radarr/Radarr-recommended-naming-scheme/):
movie folders use `Title (Year)`, episodes use `Series/Season 01`, and filenames
retain quality, audio, HDR, and release-group fields when present. Explicit
format and directory settings override the preset.

For RMM and log aggregation, pass `--log-format json`. Every emitted message is
one JSON object with a UTC timestamp, level, message, debug flag, and structured
`data` when the original message was a mapping or sequence.

Use `mnamer --serve TARGET...` to open a dependency-free web UI for remote
preview and batch processing. It binds to `127.0.0.1:8765` by default; set
`--serve-host 0.0.0.0` for a NAS LAN interface and choose another port with
`--serve-port`. Only files discovered from the supplied targets are exposed.
The service has no authentication, so keep the default loopback binding or
place a LAN/reverse-proxy access boundary in front of it.

Library integrations can use the same workflow without HTTP:

```python
from mnamer.api import preview_path, process_path

preview = preview_path("incoming/movie.mkv", settings)
destination = process_path("incoming/movie.mkv", settings)
```

Pass a configured `SettingStore` to keep provider, format, and safety settings
explicit at the integration boundary.

### Anime providers

AniList can search anime titles without credentials:

`$ mnamer --episode-api=anilist "One Piece - E1000.mkv"`

AniDB supplies episode titles and air dates. Its HTTP API requires a registered
client identifier and version, provided through `API_KEY_ANIDB` and
`API_VERSION_ANIDB` (or `api_key_anidb` in `.mnamer-v2.toml`). Use
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
