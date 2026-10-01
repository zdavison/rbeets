"""SUBPATH: a folder inside ROOT that limits a command."""

from __future__ import annotations

import os

from rbeets.protocol import BAD_ROOT, Failure


def resolve(root: str, subpath: str | None) -> str:
    """The folder that SUBPATH names inside ROOT.

    The return value keeps ROOT's own spelling, because beets stores paths
    as rbeets gives them, and an incremental import and the album filter
    match on those paths. So SUBPATH must name its folder one way only: no
    absolute path, no `..`, and no symlink on the way. Each of those could
    reach a folder inside ROOT under a second spelling, and beets would then
    hold the same album twice."""
    if not subpath:
        return root
    relative = os.path.normpath(subpath)
    if os.path.isabs(subpath) or relative == ".." or relative.startswith("../") or "/../" in f"/{subpath}/":
        raise Failure(BAD_ROOT, f"{subpath} must be a folder inside {root}, without .. or a leading /")
    folder = os.path.join(root, relative)
    if os.path.realpath(folder) != os.path.join(os.path.realpath(root), relative):
        raise Failure(BAD_ROOT, f"{subpath} leads through a symlink. Name the folder by its own path in {root}")
    if not os.path.isdir(folder):
        raise Failure(BAD_ROOT, f"{subpath} is not a folder in {root}")
    return folder


def album_folder(album) -> str:
    """The folder of an album's first track."""
    return os.path.dirname(os.fsdecode(album.items().get().path))


def in_folder(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder.rstrip("/") + "/")
