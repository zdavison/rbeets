"""Flags and paths of one command. The server parses them, so a pinned key
gets the same checks as any other."""

from __future__ import annotations

from rbeets.protocol import USAGE, Failure


def parse(command: str, args: list[str], flags: set[str], max_paths: int) -> tuple[set[str], list[str]]:
    given: set[str] = set()
    paths: list[str] = []
    for arg in args:
        if arg.startswith("-"):
            if arg not in flags:
                raise Failure(USAGE, f"{command} does not take {arg}")
            given.add(arg)
        else:
            paths.append(arg)
    if len(paths) > max_paths:
        raise Failure(USAGE, f"{command} takes at most {max_paths} path(s)")
    return given, paths
