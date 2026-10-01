"""import -A: add albums to the database as they are, with no lookups."""

from __future__ import annotations

import os

from beets.importer import ImportAbortError, ImportSession
from beets.plugins import BeetsPlugin

from rbeets.beetsenv import open_library
from rbeets.session import Session
from rbeets.state import backup


class _AsIsSession(ImportSession):
    """An import session that never asks. Autotag is off, so beets never calls
    choose_match or choose_item."""

    def should_resume(self, path: bytes) -> bool:
        return False

    def choose_match(self, task):
        raise AssertionError("autotag is off")

    def choose_item(self, task):
        raise AssertionError("autotag is off")


def import_as_is(session: Session, folder: str) -> dict:
    """import -A: add the albums under FOLDER to the database as they are."""
    backup(session.state)
    lib = open_library(session.root, session.state)
    added = 0

    def on_album_imported(lib, album) -> None:
        nonlocal added
        added += 1
        session.progress(added, None, f"{album.albumartist} - {album.album}")
        if session.stopped.is_set():
            raise ImportAbortError()

    # beets keeps listeners on the class, so a function can listen without a plugin.
    listeners = BeetsPlugin.listeners["album_imported"]
    listeners.append(on_album_imported)
    try:
        _AsIsSession(lib, None, [os.fsencode(folder)]).run()
    finally:
        listeners.remove(on_album_imported)
    return {"albums_added": added, "albums": len(lib.albums()), "tracks": len(lib.items())}
