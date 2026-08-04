from abc import ABC, abstractmethod

from mnamer import tty
from mnamer.const import SYSTEM, USAGE, VERSION
from mnamer.exceptions import (
    MnamerAbortException,
    MnamerException,
    MnamerNetworkException,
    MnamerNotFoundException,
    MnamerSkipException,
)
from mnamer.setting_store import SettingStore
from mnamer.target import Target
from mnamer.types import MessageType
from mnamer.utils import clear_cache, get_filesize, is_subtitle


class Frontend(ABC):
    settings: SettingStore
    targets: list[Target]

    def __init__(self, settings: SettingStore):
        self.settings = settings
        self.targets = Target.populate_paths(self.settings)
        tty.configure(self.settings)
        self._handle_directives()
        self._print_configuration()

    def _handle_directives(self) -> None:
        if self.settings.version:
            tty.msg(f"mnamer version {VERSION}")
            raise SystemExit(0)

        if self.settings.config_dump:
            print(self.settings.as_json())
            raise SystemExit(0)

        if self.settings.clear_cache:
            clear_cache()
            tty.msg("cache cleared", MessageType.ALERT)
            raise SystemExit(0)

        if self.settings.test:
            tty.msg("testing mode", MessageType.ALERT)
        if self.settings.config_path:
            tty.msg(
                f"loaded config from '{self.settings.config_path}'", MessageType.ALERT
            )

    def _print_configuration(self) -> None:
        tty.msg("\nsystem", debug=True)
        tty.msg(SYSTEM, debug=True)
        tty.msg("\nsettings", debug=True)
        tty.msg(self.settings.as_dict(), debug=True)
        tty.msg("\ntargets", debug=True)
        if self.targets:
            tty.msg(self.targets, debug=True)
        else:
            tty.msg([None], debug=True)

    @abstractmethod
    def launch(self):
        pass


class Cli(Frontend):
    def __init__(self, settings: SettingStore):
        super().__init__(settings)
        if not settings.targets:
            tty.error(USAGE)
            raise SystemExit(2)
        self.success_count = 0

    @property
    def total_count(self):
        return len(self.targets)

    def launch(self) -> None:
        tty.msg("Starting mnamer", MessageType.HEADING)
        self._ensure_targets()
        self._process_targets()
        self._report_results()

    def _ensure_targets(self) -> None:
        if not self.targets:
            tty.msg("", debug=True)
            tty.msg("no media files found", MessageType.ALERT)
            raise SystemExit(0)

    def _process_targets(self) -> None:
        for target in self.targets:
            if not self._process_target(target):
                break

    def _process_target(self, target: Target) -> bool:
        """Process one target and return whether the caller should continue."""
        self._announce_file(target)
        self._list_details(target)

        # find match for target
        matches = []
        try:
            matches = target.query()
        except MnamerNotFoundException:
            tty.msg("no matches found", MessageType.ALERT)
        except MnamerNetworkException:
            tty.msg("network error", MessageType.ALERT)
        if target.smart_match_error:
            tty.msg(target.smart_match_error, MessageType.ALERT)
        if not matches and self.settings.no_guess:
            tty.msg("skipping (--no-guess)", MessageType.ALERT)
            return True
        try:
            if self.settings.batch:
                match = matches[0] if matches else target.metadata
            elif not matches:
                match = tty.metadata_guess(target.metadata)
            else:
                match = tty.metadata_prompt(matches)
        except MnamerSkipException:
            tty.msg("skipping (user request)", MessageType.ALERT)
            return True
        except MnamerAbortException:
            tty.msg("aborting (user request)", MessageType.ERROR)
            return False
        target.metadata.update(match)

        if is_subtitle(target.metadata.container) and not target.metadata.language_sub:
            if self.settings.batch:
                tty.msg(
                    "skipping (subtitle language can't be detected)",
                    MessageType.ALERT,
                )
                return True
            try:
                target.metadata.language_sub = tty.subtitle_prompt()
            except MnamerSkipException:
                tty.msg("skipping (user request)", MessageType.ALERT)
                return True
            except MnamerAbortException:
                tty.msg("aborting (user request)", MessageType.ERROR)
                return False

        # sanity check move
        if target.destination == target.source:
            tty.msg(
                "skipping (source and destination paths are the same)",
                MessageType.ALERT,
            )
            return True
        if self.settings.no_overwrite and target.destination.exists():
            tty.msg("skipping (--no-overwrite)", MessageType.ALERT)
            return True

        self._rename_and_move_file(target)
        return True

    def _announce_file(self, target: Target):
        media_type = target.metadata.to_media_type().value.title()
        description = (
            f"{media_type} Subtitle"
            if is_subtitle(target.metadata.container)
            else media_type
        )
        filename_label = target.source.name
        filesize_label = get_filesize(target.source)
        tty.msg(
            f'\nProcessing {description} "{filename_label}" ({filesize_label})',
            MessageType.HEADING,
        )
        tty.msg(target.source, debug=True)

    def _list_details(self, target: Target):
        tty.msg(f"using {target.provider_type.value}", MessageType.ALERT, debug=True)
        tty.msg("\nsearch parameters", debug=True)
        tty.msg(target.metadata.as_dict(), debug=True)
        tty.msg("", debug=True)

    def _rename_and_move_file(self, target: Target):
        tty.msg(
            f"moving to {target.destination.absolute()}",
            MessageType.SUCCESS,
        )
        if self.settings.test:
            self.success_count += 1
            return
        try:
            target.relocate()
        except MnamerException:
            tty.msg("FAILED!", MessageType.ERROR)
        else:
            tty.msg("OK!", MessageType.SUCCESS)
            if target.artwork_error:
                tty.msg(
                    f"artwork unavailable: {target.artwork_error}",
                    MessageType.ALERT,
                )
            elif target.artwork_downloaded:
                tty.msg(
                    f"downloaded {len(target.artwork_downloaded)} artwork file(s)",
                    MessageType.SUCCESS,
                )
            if target.hook_error:
                tty.msg(
                    f"post-action hook unavailable: {target.hook_error}",
                    MessageType.ALERT,
                )
            self.success_count += 1

    def _report_results(self) -> None:
        if self.success_count == 0:
            message_type = MessageType.ERROR
        elif self.success_count == self.total_count:
            message_type = MessageType.SUCCESS
        else:
            message_type = MessageType.ALERT
        tty.msg(
            f"\n{self.success_count} out of {self.total_count} files processed successfully",
            message_type,
        )


class Gui(Frontend):
    def launch(self):
        pass  # to be implemented in v3


class Tui(Cli):
    """Textual preview frontend sharing target discovery with the CLI."""

    def launch(self) -> None:
        from mnamer.journal import start_session
        from mnamer.tui import run_tui

        start_session()
        self.success_count = run_tui(self.targets, self.settings)
        self._report_results()


class Watch(Cli):
    """Continuously process files created in one or more target folders."""

    def launch(self) -> None:
        from mnamer.journal import start_session
        from mnamer.watch import run_watch

        start_session()
        tty.msg("Starting mnamer watch", MessageType.HEADING)
        if self.targets:
            self._process_targets()
        run_watch(self.settings, self._process_watch_target)

    def _process_watch_target(self, path):
        if not path.is_file():
            return None
        target = Target(path, self.settings)
        if not self._process_target(target):
            return None
        if not target.source.exists() and target.destination.exists():
            return target.destination
        return None


class Undo(Frontend):
    """Replay the most recent CLI relocation session in reverse order."""

    def launch(self) -> None:
        from mnamer.journal import undo_last_session

        result = undo_last_session()
        if result.moved:
            tty.msg(
                f"undid {result.moved} recorded move(s)",
                MessageType.SUCCESS,
            )
        if result.skipped:
            tty.msg(
                f"skipped {result.skipped} move(s) that were no longer safe",
                MessageType.ALERT,
            )
        if not result.moved and not result.skipped:
            tty.msg("no recorded moves to undo", MessageType.ALERT)
