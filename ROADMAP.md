# ROADMAP

mnamer parses media filenames, resolves metadata from TVDb/TvMaze/TMDb/OMDb, and renames/moves files using customizable format templates.

## Planned Features

### Providers
- Add AniDB and AniList providers for anime; current TVDb anime mapping is lossy on multi-season shows with absolute numbering
- Fanart.tv integration for artwork download alongside rename (poster, fanart, logo)
- MusicBrainz provider for audiobook and music-video files
- Local-first NFO provider — parse adjacent `.nfo` / Jellyfin / Plex metadata instead of re-querying every run
- Provider circuit-breaker so one flaky API doesn't stall a batch

### Matching
- Embedding-based title match (sentence-transformers) for releases with mangled titles, behind a `--smart-match` flag
- Year-range matching when parsed year is off by one (common for late-Dec releases)
- Multi-file episode detection: `S01E01E02`, `-E01-E02`, and loose-case pack files
- Subtitle language auto-detection via `langdetect` when filename lacks a language code
- HDR/DV/Atmos tags extracted from filename + optional ffprobe for format template variables (`{hdr}`, `{audio}`)

### UX
- TUI mode (`textual`) with batch preview, per-file accept/reject, and inline metadata edit
- `--watch` mode using `watchdog` for Radarr/Sonarr-style ingestion folders
- `--undo` that replays the last session's moves from a rotating journal
- Post-action hooks (`--on-success <cmd>`) for Plex/Jellyfin library refresh
- `--dry-run-diff` showing a unified diff of the plan, friendly for copy/paste review

### Ops
- Move the `.mnamer-v2.json` loader off JSON to TOML for comments and trailing commas
- Structured JSON log output (`--log-format json`) for RMM/log aggregation
- Docker image: multi-arch (arm64 for Synology/UGREEN NAS), non-root user, volume-mapped config

## Competitive Research

- **FileBot** — Closed-source gold standard; beats mnamer on anime matching and format presets. Worth studying their format spec for parity.
- **Sonarr / Radarr** — Continuous-watch + PVR focus; mnamer is the batch-rename niche, but their rename-on-import API surface is a model for hooks
- **tinyMediaManager** — GUI-driven, NFO-first. Reinforces the case for a local-NFO provider
- **beets** (music) — Plugin architecture + replay-gain hooks; pattern to borrow for mnamer plugins

## Nice-to-Haves

- Plex/Jellyfin direct library refresh on success (no need for external cron)
- OpenSubtitles auto-download keyed to matched episode/movie ID
- Web UI (`--serve`) for remote NAS use
- Burn-in thumbnail generator for archive indexes
- Community format-preset gallery loaded from a Git repo

## Open-Source Research (Round 2)

### Related OSS Projects
- https://github.com/Sonarr/Sonarr — TV automation standard; RSS-driven, push-to-client, ecosystem leader; mnamer's "indirect Sonarr integration" could become a supported post-processing hook
- https://github.com/Radarr/Radarr — Sonarr's movie fork; same plugin + post-processing model
- https://github.com/StrawberryStego/Simpler-FileBot — PySide6 GUI batch renamer using `guessit`; direct OSS alternative to the paid FileBot
- https://github.com/rmatil/filebot — community mirror/reference for FileBot's AMC script patterns (archive extract → identify → rename → Plex notify)
- https://trash-guides.info/Radarr/Radarr-recommended-naming-scheme/ — TRaSH Guides' canonical naming scheme (TMDb-first) — the community-standard format preset
- https://github.com/guessit-io/guessit — the underlying filename-parsing library; worth bundling as a fallback provider when all online providers fail
- https://github.com/topics/media-manager — adjacent tooling (tinyMediaManager, Jellyfin-compat tools) for cross-reference

### Features to Borrow
- Post-process hook contract (Sonarr/Radarr) — emit environment variables (`mnamer_source_path`, `mnamer_target_path`, `mnamer_imdb_id`, etc.) and invoke a user-supplied script after each rename — unlocks Plex/Jellyfin/Sonarr triggers without bespoke code
- TRaSH-compatible default preset (TRaSH Guides) — ship it as `--preset trash` so new users get the community-standard layout instantly
- guessit fallback provider (guessit-io) — when TVDb/TMDb/OMDb all miss, parse filename heuristically and propose rather than skipping
- PySide6 GUI reference (Simpler-FileBot) — informs the long-planned `--serve` web UI; a desktop GUI is another viable distribution form
- FileBot AMC-style "unpack → identify → move → notify" macro (rmatil/filebot) — bundle as `mnamer watch <dir>` for a true unattended workflow matching the FileBot automation story
- Plex-only-changed-libraries optimization (AMC script pattern) — when notifying Plex, scan only the library whose file actually changed, not the whole server

### Patterns & Architectures Worth Studying
- Provider abstraction layer (already present; see TVDb/TvMaze/TMDb/OMDb) — extend to accept arbitrary user-supplied providers via entrypoints; AniDB, Kitsu, etc. become community plugins without core changes
- Separate input/output directories as a hard contract (FileBot AMC convention) — `/downloads/complete → /media` — prevents half-renamed states and makes rollback trivial
- Dry-run as a first-class mode rather than a flag (organize/phockup idiom) — considered safer than `--test` buried in flags
- CLI + library dual-surface — Sonarr/Radarr expose REST APIs that downstream tools call; mnamer already has a clean CLI, a matching `mnamer.api` module would let `improve-repo`-style agents call it programmatically
