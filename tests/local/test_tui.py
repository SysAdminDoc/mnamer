import asyncio
from pathlib import Path

import pytest

# Optional UI dependency: this test remains a no-op in the default install.
pytest.importorskip("textual")
from textual.widgets import Input  # noqa: E402

from mnamer.metadata import MetadataMovie  # noqa: E402
from mnamer.setting_store import SettingStore  # noqa: E402
from mnamer.tui import create_tui_app  # noqa: E402

pytestmark = pytest.mark.local


class FakeTarget:
    def __init__(self, source: Path, name: str):
        self.source = source
        self.metadata = MetadataMovie(name=name, year="2024")
        self.smart_match_error = None
        self.relocated = False

    @property
    def destination(self):
        return self.source.parent / f"{self.metadata.name}.mkv"

    def query(self):
        return [MetadataMovie(name="Resolved title", year="2024")]

    def relocate(self):
        self.relocated = True


def test_tui_preview_edit_accept_and_reject(tmp_path):
    async def exercise():
        first = FakeTarget(tmp_path / "first.mkv", "First")
        second = FakeTarget(tmp_path / "second.mkv", "Second")
        app = create_tui_app([first, second], SettingStore())

        async with app.run_test() as pilot:
            await pilot.pause()
            editor = app.query_one("#edit-name", Input)
            editor.value = "Edited title"
            app._save_editor()
            assert first.metadata.name == "Edited Title"

            app._accept_current()
            assert first.relocated is True
            assert app.previews[0].status == "accepted"

            app._reject_current()
            assert second.relocated is False
            assert app.previews[1].status == "rejected"

    asyncio.run(exercise())
