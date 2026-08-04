"""Built-in naming presets."""

TRASH_PRESET = {
    "movie_directory": None,
    "movie_format": "{name} ({year})/{name} ({year}) - {quality} {audio} {hdr} - {group}.{extension}",
    "episode_directory": None,
    "episode_format": "{series}/Season {season:02}/{series} - S{season:02}E{episode:02} - {title} - {quality} {audio} {hdr} - {group}.{extension}",
}

PRESETS = {"trash": TRASH_PRESET}
