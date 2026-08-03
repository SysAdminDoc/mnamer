from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from mnamer.exceptions import MnamerException
from mnamer.setting_store import SettingStore
from mnamer.target import Target

_EDIT_FIELDS = (
    "name",
    "series",
    "title",
    "year",
    "season",
    "episode",
    "language_sub",
    "hdr",
    "audio",
)


@dataclasses.dataclass
class Preview:
    target: Target
    status: str = "loading"
    error: str | None = None


def create_tui_app(targets: Sequence[Target], settings: SettingStore) -> Any:
    """Build the optional Textual application without importing it by default."""
    try:
        from textual.app import App
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Button, DataTable, Footer, Header, Input, Static
    except ImportError as error:
        raise MnamerException(
            "the TUI requires the optional dependency; install "
            'mnamer with `pip install "mnamer[tui]"`'
        ) from error

    class PreviewApp(App):
        TITLE = "mnamer preview"
        CSS = """
        #layout { height: 1fr; padding: 1 2; }
        #preview { height: 1fr; }
        #editor { height: auto; min-height: 3; }
        #editor Input { width: 1fr; margin: 0 1; }
        #actions { height: auto; align: center middle; }
        #actions Button { margin: 1 2; }
        #help { height: auto; padding: 0 1; color: $text-muted; }
        """
        BINDINGS = [
            ("a", "accept", "Accept"),
            ("r", "reject", "Reject"),
            ("s", "save", "Save metadata"),
            ("q", "quit", "Quit"),
        ]

        def __init__(self):
            super().__init__()
            self.settings = settings
            self.previews = [Preview(target) for target in targets]
            self.current_index = 0
            self.success_count = 0

        def compose(self):
            yield Header()
            with Vertical(id="layout"):
                yield Static(
                    "Review provider matches, edit metadata, then accept or reject "
                    "each file.",
                    id="help",
                )
                yield DataTable(id="preview")
                with Horizontal(id="editor"):
                    for field in _EDIT_FIELDS:
                        yield Input(
                            placeholder=field,
                            id=f"edit-{field}",
                        )
                with Horizontal(id="actions"):
                    yield Button("Save", id="save", variant="primary")
                    yield Button("Accept", id="accept", variant="success")
                    yield Button("Reject", id="reject", variant="warning")
                    yield Button("Quit", id="quit", variant="error")
            yield Footer()

        def on_mount(self):
            table = self.query_one(DataTable)
            table.cursor_type = "row"
            table.add_column("Status", key="status")
            table.add_column("Source", key="source")
            table.add_column("Destination", key="destination")
            for index, preview in enumerate(self.previews):
                self._prepare_preview(preview)
                table.add_row(
                    preview.status,
                    str(preview.target.source),
                    self._destination(preview.target),
                    key=str(index),
                )
            if self.previews:
                self._select_preview(0)

        @staticmethod
        def _destination(target: Target) -> str:
            try:
                return str(target.destination)
            except (AttributeError, MnamerException, TypeError, ValueError):
                return "unresolved"

        @staticmethod
        def _prepare_preview(preview: Preview) -> None:
            try:
                matches = preview.target.query()
            except MnamerException as error:
                preview.error = str(error)
                preview.status = "error"
                return
            if matches:
                preview.target.metadata.update(matches[0])
                preview.status = "ready"
            else:
                preview.status = "ready (guess)"

        def _select_preview(self, index: int) -> None:
            if not 0 <= index < len(self.previews):
                return
            self.current_index = index
            metadata = self.previews[index].target.metadata
            for field in _EDIT_FIELDS:
                editor = self.query_one(f"#edit-{field}", Input)
                available = hasattr(metadata, field)
                editor.disabled = not available
                value = getattr(metadata, field, None)
                editor.value = "" if value is None else str(value)

        def on_data_table_row_selected(self, event: Any) -> None:
            self._select_preview(event.cursor_row)

        def _current_preview(self) -> Preview | None:
            if not self.previews:
                return None
            return self.previews[self.current_index]

        def _save_editor(self) -> None:
            preview = self._current_preview()
            if preview is None:
                return
            metadata = preview.target.metadata
            for field in _EDIT_FIELDS:
                if not hasattr(metadata, field):
                    continue
                editor = self.query_one(f"#edit-{field}", Input)
                setattr(metadata, field, editor.value.strip() or None)
            self._refresh_row()

        def _refresh_row(self) -> None:
            preview = self._current_preview()
            if preview is None:
                return
            table = self.query_one(DataTable)
            table.update_cell(
                str(self.current_index),
                "destination",
                self._destination(preview.target),
            )

        def _set_status(self, status: str) -> None:
            preview = self._current_preview()
            if preview is None:
                return
            preview.status = status
            self.query_one(DataTable).update_cell(
                str(self.current_index), "status", status
            )

        def _accept_current(self) -> None:
            preview = self._current_preview()
            if preview is None or preview.status in {"accepted", "rejected"}:
                return
            self._save_editor()
            target = preview.target
            if target.destination == target.source:
                self._set_status("skipped (unchanged)")
                return
            if self.settings.no_overwrite and target.destination.exists():
                self._set_status("skipped (exists)")
                return
            try:
                if not self.settings.test:
                    target.relocate()
            except MnamerException as error:
                preview.error = str(error)
                self._set_status("error")
                return
            self.success_count += 1
            self._set_status("accepted")
            self._select_preview(self.current_index + 1)

        def _reject_current(self) -> None:
            if self._current_preview() is None:
                return
            self._set_status("rejected")
            self._select_preview(self.current_index + 1)

        def action_save(self) -> None:
            self._save_editor()

        def action_accept(self) -> None:
            self._accept_current()

        def action_reject(self) -> None:
            self._reject_current()

        async def action_quit(self) -> None:
            self.exit()

        def on_button_pressed(self, event: Any) -> None:
            actions: dict[str, Any] = {
                "save": self._save_editor,
                "accept": self._accept_current,
                "reject": self._reject_current,
                "quit": self.exit,
            }
            action = actions.get(event.button.id)
            if action:
                action()

    return PreviewApp()


def run_tui(targets: Sequence[Target], settings: SettingStore) -> int:
    """Run the interactive preview and return the number of accepted files."""
    app = create_tui_app(targets, settings)
    app.run()
    return app.success_count
