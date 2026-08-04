"""Optional post-action commands for successful relocations."""

from __future__ import annotations

import dataclasses
import os
import shlex
import subprocess
from pathlib import Path

from mnamer.metadata import Metadata

HOOK_TIMEOUT_SECONDS = 60.0


@dataclasses.dataclass(frozen=True)
class HookResult:
    error: str | None = None


def _command_args(command: str) -> list[str]:
    args = shlex.split(command, posix=os.name != "nt")
    if os.name == "nt":
        args = [
            arg[1:-1]
            if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in "\"'"
            else arg
            for arg in args
        ]
    return args


def _hook_environment(
    source: Path, destination: Path, metadata: Metadata
) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "MNAMER_SOURCE_PATH": str(source.absolute()),
            "MNAMER_TARGET_PATH": str(destination.absolute()),
            "MNAMER_MEDIA_TYPE": metadata.to_media_type().value,
            "MNAMER_SUCCESS": "1",
        }
    )
    for key, value in metadata.as_dict().items():
        if not key.startswith("id_") or value is None:
            continue
        environment[f"MNAMER_{key.upper()}"] = str(value)
    return environment


def run_success_hook(
    command: str, source: Path, destination: Path, metadata: Metadata
) -> HookResult:
    """Run a configured command and return a non-fatal error description."""
    try:
        args = _command_args(command)
    except ValueError as error:
        return HookResult(f"invalid command: {error}")
    if not args:
        return HookResult("command is empty")
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            check=False,
            env=_hook_environment(source, destination, metadata),
            shell=False,
            text=True,
            timeout=HOOK_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return HookResult(f"command not found: {args[0]}")
    except OSError as error:
        return HookResult(str(error))
    except subprocess.TimeoutExpired:
        return HookResult(f"command timed out after {HOOK_TIMEOUT_SECONDS:g}s")
    if result.returncode == 0:
        return HookResult()
    detail = (result.stderr or result.stdout or "").strip()
    suffix = f": {detail}" if detail else ""
    return HookResult(f"command exited with status {result.returncode}{suffix}")
