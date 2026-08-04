from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from mnamer.diff import relocation_diff
from mnamer.frontends import Cli

pytestmark = pytest.mark.local


def test_relocation_diff_is_unified_and_copyable(tmp_path):
    source = tmp_path / "incoming.mkv"
    destination = tmp_path / "library" / "Movie (2024).mkv"

    diff = relocation_diff(source, destination)

    assert diff == (
        "--- source\n"
        "+++ destination\n"
        "@@ -1 +1 @@\n"
        f"-{source.absolute()}\n"
        f"+{destination.absolute()}"
    )


def test_cli_dry_run_diff_does_not_relocate(tmp_path):
    frontend = object.__new__(Cli)
    frontend.settings = SimpleNamespace(dry_run_diff=True, test=False)
    frontend.success_count = 0
    target = SimpleNamespace(
        source=tmp_path / "incoming.mkv",
        destination=tmp_path / "Movie.mkv",
        relocate=Mock(),
    )

    with patch("mnamer.frontends.tty.msg") as msg:
        frontend._rename_and_move_file(target)

    target.relocate.assert_not_called()
    assert frontend.success_count == 1
    assert msg.call_args_list[0].args[0] == "dry-run diff"
    assert "--- source" in msg.call_args_list[1].args[0]
