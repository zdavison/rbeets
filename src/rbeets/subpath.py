"""SUBPATH: a folder inside ROOT that limits a command."""

from __future__ import annotations

import os

from rbeets.protocol import BAD_ROOT, Failure


def resolve(root: str, subpath: str | None) -> str:
    """The folder that SUBPATH names inside ROOT.

    The check resolves symlinks, so a symlink cannot lead out of ROOT. The
    return value keeps ROOT's own spelling, because beets stores paths as
    rbeets gives them, and an incremental import matches on those paths."""
    if not subpath:
        return root
    folder = os.path.normpath(os.path.join(root, subpath))
    real_root = os.path.realpath(root)
    if os.path.commonpath([real_root, os.path.realpath(folder)]) != real_root:
        raise Failure(BAD_ROOT, f"{subpath} is outside {root}")
    if not os.path.isdir(folder):
        raise Failure(BAD_ROOT, f"{subpath} is not a folder in {root}")
    return folder


def album_folder(album) -> str:
    """The folder of an album's first track."""
    return os.path.dirname(os.fsdecode(album.items().get().path))


def in_folder(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder.rstrip("/") + "/")
