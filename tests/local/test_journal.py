import pytest

from mnamer import journal

pytestmark = pytest.mark.local


@pytest.fixture
def journal_path(tmp_path, monkeypatch):
    path = tmp_path / "moves.jsonl"
    monkeypatch.setattr(journal, "JOURNAL_PATH", path)
    return path


def test_journal_rotates_sessions(journal_path):
    source = journal_path.parent / "incoming.mkv"
    destination = journal_path.parent / "library" / "movie.mkv"

    journal.start_session()
    journal.record_move(source, destination)
    journal.start_session()

    assert journal.last_session_moves() == []
    assert journal._archive_path(1).exists()
    assert (
        journal._archive_path(1).read_text(encoding="utf-8").find('"type": "move"') >= 0
    )


def test_undo_replays_moves_in_reverse_and_marks_session(journal_path):
    base = journal_path.parent
    source_a = base / "incoming" / "a.mkv"
    source_b = base / "incoming" / "b.mkv"
    destination_a = base / "library" / "a.mkv"
    destination_b = base / "library" / "b.mkv"
    destination_a.parent.mkdir()
    destination_a.write_bytes(b"a")
    destination_b.write_bytes(b"b")

    journal.start_session()
    journal.record_move(source_a, destination_a)
    journal.record_move(source_b, destination_b)

    result = journal.undo_last_session()

    assert result == journal.UndoResult(moved=2, skipped=0)
    assert source_a.read_bytes() == b"a"
    assert source_b.read_bytes() == b"b"
    assert not destination_a.exists()
    assert not destination_b.exists()
    assert journal.last_session_moves() == []
    assert journal.undo_last_session() == journal.UndoResult()


def test_undo_skips_conflicting_or_missing_paths(journal_path):
    base = journal_path.parent
    source = base / "incoming" / "movie.mkv"
    destination = base / "library" / "movie.mkv"
    source.parent.mkdir()
    source.write_bytes(b"new")

    journal.start_session()
    journal.record_move(source, destination)

    result = journal.undo_last_session()

    assert result == journal.UndoResult(skipped=1)
    assert source.read_bytes() == b"new"
