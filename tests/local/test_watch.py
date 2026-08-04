import threading
from pathlib import Path

import pytest

pytest.importorskip("watchdog")
from watchdog.events import FileCreatedEvent, FileMovedEvent  # noqa: E402

from mnamer.exceptions import MnamerException  # noqa: E402
from mnamer.setting_store import SettingStore  # noqa: E402
from mnamer.watch import create_event_handler, run_watch  # noqa: E402

pytestmark = pytest.mark.local


def test_event_handler_filters_extensions_and_ignores(tmp_path):
    settings = SettingStore(mask=[".mkv"], ignore=["sample"])
    queued: list[Path] = []
    handler = create_event_handler(settings, queued.append)
    media = tmp_path / "movie.mkv"
    sample = tmp_path / "sample.mkv"
    text = tmp_path / "notes.txt"

    handler.on_created(FileCreatedEvent(str(media)))
    handler.on_created(FileCreatedEvent(str(sample)))
    handler.on_created(FileCreatedEvent(str(text)))

    assert queued == [media.absolute()]


def test_event_handler_queues_moved_destination(tmp_path):
    settings = SettingStore(mask=[".mkv"])
    queued: list[Path] = []
    handler = create_event_handler(settings, queued.append)

    handler.on_moved(
        FileMovedEvent(str(tmp_path / "partial.tmp"), str(tmp_path / "movie.mkv"))
    )

    assert queued == [(tmp_path / "movie.mkv").absolute()]


def test_run_watch_processes_event_and_stops(tmp_path):
    settings = SettingStore(
        targets=[tmp_path],
        mask=[".mkv"],
        recurse=True,
    )
    media = tmp_path / "movie.mkv"
    processed: list[Path] = []
    stop_event = threading.Event()

    class FakeObserver:
        def __init__(self):
            self.handler = None
            self.schedule_args = []
            self.started = False
            self.stopped = False

        def schedule(self, handler, path, recursive):
            self.handler = handler
            self.schedule_args.append((path, recursive))

        def start(self):
            self.started = True
            media.write_bytes(b"video")
            self.handler.on_created(FileCreatedEvent(str(media)))
            stop_event.set()

        def stop(self):
            self.stopped = True

        def join(self):
            pass

    observer = FakeObserver()

    run_watch(
        settings,
        lambda path: processed.append(path),
        observer_factory=lambda: observer,
        stop_event=stop_event,
        settle_seconds=0,
        poll_interval=0.01,
    )

    assert observer.started is True
    assert observer.stopped is True
    assert observer.schedule_args == [(str(tmp_path.absolute()), True)]
    assert processed == [media.absolute()]


def test_run_watch_rejects_missing_paths(tmp_path):
    settings = SettingStore(targets=[tmp_path / "missing"])

    with pytest.raises(MnamerException, match="watch path does not exist"):
        run_watch(settings, lambda _path: None)
