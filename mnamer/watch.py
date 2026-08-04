"""Watchdog integration for continuously processing ingestion folders."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from queue import Empty, Queue
from threading import Event
from typing import Any

from mnamer.exceptions import MnamerException
from mnamer.setting_store import SettingStore
from mnamer.tty import msg
from mnamer.types import MessageType
from mnamer.utils import filter_blacklist, filter_containers

PathProcessor = Callable[[Path], Path | None]
ObserverFactory = Callable[[], Any]

_DEBOUNCE_SECONDS = 1.0
_STABLE_SECONDS = 0.75
_STABILITY_TIMEOUT_SECONDS = 30.0


def _is_candidate(path: Path, settings: SettingStore) -> bool:
    """Return whether a filesystem event can represent a media target."""
    if not filter_containers([path], settings.mask):
        return False
    if not filter_blacklist([path], settings.ignore):
        return False
    return True


def create_event_handler(
    settings: SettingStore, enqueue: Callable[[Path], None]
) -> Any:
    """Create a lazy watchdog handler without making the extra mandatory."""
    try:
        from watchdog.events import FileSystemEventHandler
    except ImportError as error:
        raise MnamerException(
            "watch mode requires the optional dependency; install with "
            '`pip install "mnamer[watch]"`'
        ) from error

    class WatchEventHandler(FileSystemEventHandler):
        def _handle(self, raw_path: str) -> None:
            path = Path(raw_path).absolute()
            if _is_candidate(path, settings):
                enqueue(path)

        def on_created(self, event) -> None:
            if not event.is_directory:
                self._handle(event.src_path)

        def on_closed(self, event) -> None:
            if not event.is_directory:
                self._handle(event.src_path)

        def on_moved(self, event) -> None:
            if not event.is_directory:
                self._handle(event.dest_path)

    return WatchEventHandler()


def _watch_roots(settings: SettingStore) -> list[Path]:
    if not settings.targets:
        raise MnamerException("watch mode requires at least one target folder")
    roots = set()
    for target in settings.targets:
        path = Path(target).absolute()
        if path.is_dir():
            roots.add(path)
        elif path.is_file():
            roots.add(path.parent)
        else:
            raise MnamerException(f"watch path does not exist: {path}")
    return sorted(roots)


def _wait_for_stable(
    path: Path,
    settle_seconds: float = _STABLE_SECONDS,
    timeout_seconds: float = _STABILITY_TIMEOUT_SECONDS,
) -> bool:
    """Wait until a copied file stops changing before handing it to guessit."""
    deadline = time.monotonic() + timeout_seconds
    previous: tuple[int, int] | None = None
    stable_since: float | None = None
    while time.monotonic() <= deadline:
        try:
            stat = path.stat()
        except OSError:
            previous = None
            stable_since = None
        else:
            signature = (stat.st_size, stat.st_mtime_ns)
            now = time.monotonic()
            if signature != previous:
                previous = signature
                stable_since = now
            elif settle_seconds <= 0 or (
                stable_since is not None and now - stable_since >= settle_seconds
            ):
                return True
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
    return False


def run_watch(
    settings: SettingStore,
    process_target: PathProcessor,
    *,
    observer_factory: ObserverFactory | None = None,
    stop_event: Event | None = None,
    poll_interval: float = 0.5,
    settle_seconds: float = _STABLE_SECONDS,
) -> None:
    """Run the watcher until interrupted or an injected stop event is set."""
    roots = _watch_roots(settings)
    if observer_factory is None:
        try:
            from watchdog.observers import Observer
        except ImportError as error:
            raise MnamerException(
                "watch mode requires the optional dependency; install with "
                '`pip install "mnamer[watch]"`'
            ) from error
        observer_factory = Observer

    pending: Queue[Path] = Queue()
    last_enqueued: dict[Path, float] = {}
    suppressed: dict[Path, float] = {}
    clock = time.monotonic

    def enqueue(path: Path) -> None:
        now = clock()
        previous = last_enqueued.get(path)
        if previous is not None and now - previous < _DEBOUNCE_SECONDS:
            return
        last_enqueued[path] = now
        pending.put(path)

    handler = create_event_handler(settings, enqueue)
    observer = observer_factory()
    for root in roots:
        observer.schedule(handler, str(root), recursive=settings.recurse)

    started = False
    try:
        observer.start()
        started = True
        msg(
            f"watching {', '.join(str(root) for root in roots)} (press Ctrl-C to stop)",
            MessageType.HEADING,
        )
        while stop_event is None or not stop_event.is_set() or not pending.empty():
            try:
                path = pending.get(timeout=max(0.01, poll_interval))
            except Empty:
                continue
            expiry = suppressed.get(path)
            if expiry is not None:
                if clock() <= expiry:
                    continue
                del suppressed[path]
            if not path.exists() or not _is_candidate(path, settings):
                continue
            if not _wait_for_stable(path, settle_seconds=settle_seconds):
                msg(f"skipping unstable file: {path}", MessageType.ALERT)
                continue
            try:
                destination = process_target(path)
            except MnamerException as error:
                msg(f"watch processing failed: {error}", MessageType.ERROR)
                continue
            except OSError as error:
                msg(f"watch processing failed: {error}", MessageType.ERROR)
                continue
            if destination:
                suppressed[destination.absolute()] = clock() + _DEBOUNCE_SECONDS
    except KeyboardInterrupt:
        msg("stopping watch", MessageType.ALERT)
    finally:
        if started:
            observer.stop()
            observer.join()
