import pytest

from mnamer.language import Language
from mnamer.setting_store import SettingStore
from mnamer.subtitles import detect_subtitle_language
from mnamer.target import Target
from mnamer.types import MediaType

pytestmark = pytest.mark.local

ENGLISH_SUBTITLE = """1
00:00:01,000 --> 00:00:04,000
This is a sufficiently long English subtitle sentence for detection.

2
00:00:05,000 --> 00:00:08,000
The next line gives the detector more context about the dialogue.
"""

GERMAN_SUBTITLE = """1
00:00:01,000 --> 00:00:04,000
Dies ist ein ausreichend langer deutscher Untertitel zur Erkennung.

2
00:00:05,000 --> 00:00:08,000
Die nächste Zeile liefert dem Detektor zusätzlichen Kontext.
"""


@pytest.mark.parametrize(
    ("suffix", "contents", "expected"),
    [
        (".srt", ENGLISH_SUBTITLE, Language.parse("en")),
        (".sub", GERMAN_SUBTITLE, Language.parse("de")),
    ],
)
def test_detect_subtitle_language(suffix, contents, expected, tmp_path):
    source = tmp_path / f"subtitle{suffix}"
    source.write_text(contents, encoding="utf-8")

    assert detect_subtitle_language(source) == expected


def test_detect_subtitle_language__ignores_idx_and_short_text(tmp_path):
    idx = tmp_path / "subtitle.idx"
    idx.write_text(ENGLISH_SUBTITLE, encoding="utf-8")
    short = tmp_path / "short.srt"
    short.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello", encoding="utf-8")

    assert detect_subtitle_language(idx) is None
    assert detect_subtitle_language(short) is None


def test_target__detects_subtitle_language_without_filename_code(tmp_path):
    source = tmp_path / "Example Movie 2001.srt"
    source.write_text(ENGLISH_SUBTITLE, encoding="utf-8")

    target = Target(
        source,
        SettingStore(media=MediaType.MOVIE),
    )

    assert target.metadata.language_sub == Language.parse("en")
