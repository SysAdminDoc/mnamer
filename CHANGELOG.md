# Changelog

All notable changes to mnamer will be documented in this file.

## [Unreleased]

- Added AniDB XML and AniList GraphQL providers for anime episode metadata.
- Added anime provider selection and AniDB/AniList id overrides to the CLI and
  configuration file.
- Added opt-in Fanart.tv poster, fanart, and logo downloads alongside relocated
  media files.
- Added MusicBrainz metadata lookup for music tracks and audiobook chapters,
  including automatic audio-container detection and configurable music formats.
- Added local-first NFO/XML/JSON sidecar metadata for movie, episode, and music
  targets with online-provider fallback.
- Added per-provider circuit breaking after repeated network failures so batch
  processing fails fast while an API is unavailable.
- TMDb movie title searches now include the adjacent release years to tolerate
  late-December catalog and filename year boundaries.
- Multi-episode filenames now retain all detected episode numbers and expose an
  `{episode_range}` format value while preserving the existing first-episode
  provider lookup behavior.
- Text-based subtitles without a filename language code now receive a
  conservative automatic language detection result when the dialogue is clear.
- Added opt-in `--smart-match` semantic title reranking using the optional
  `sentence-transformers` extra.
- Added `{hdr}` and `{audio}` format values with filename and optional ffprobe
  detection for HDR, Dolby Vision, HLG, and Atmos tags.
- Added optional `--tui` Textual preview mode with inline edits and per-file
  accept/reject actions.
- Added optional `--watch` mode using watchdog for stable-file processing in
  Radarr/Sonarr-style ingestion folders.
- Added `--undo` with a rotating move journal and safe reverse-order replay.
- Added `--on-success` post-action commands with source, destination, media, and
  provider-id environment variables.
- Added `--dry-run-diff` unified relocation plans without filesystem changes.
- TOML is now the default `.mnamer-v2.toml` configuration format, with comments,
  trailing commas, and legacy JSON loading retained.
- Added `--log-format json` machine-readable output for RMM and log aggregation.
- Updated the Docker image for amd64/arm64 Buildx releases, non-root execution,
  and bind-mounted `/config` and `/mnt` volumes.
- Added a dependency-free `--serve` web UI with JSON preview/process endpoints
  for remote NAS workflows.
- Added optional ffmpeg-backed burned-in JPEG thumbnails for moved movies and
  episodes via `--thumbnails`.
- Added a `--preset trash` naming preset with explicit-format overrides.

## [v0.1.0] - %Y->- (HEAD -> main, origin/main, origin/HEAD)

- Skip multi-part episode test
- Changed: Bump actions/checkout from 4 to 6
- Fixed: Fix uv installation command in README
- Run push workflow on main branch and schedules only
- Added: Add type ignore for attr-defined on session assignment
- Removed: Drop Python 3.11 support and update dev dependencies
- Changed: Updates python compatibility, integrates uv, repalces black with ruff
- Fixed: Fix typos
- Inherits secrets between jobs
- Prevents publish attempt from on-schedule event
