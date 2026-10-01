"""stats: count albums and tracks, and list albums with no MusicBrainz album ID."""

from __future__ import annotations

from rbeets import subpath
from rbeets.beetsenv import open_library
from rbeets.protocol import USAGE, Failure
from rbeets.session import Session


def run(session: Session, args: list[str]) -> dict:
    if args:
        raise Failure(USAGE, "stats takes no arguments")
    lib = open_library(session.root, session.state)
    albums = list(lib.albums())
    missing = [
        {
            "albumartist": album.albumartist,
            "album": album.album,
            "path": subpath.album_folder(album),
        }
        for album in albums
        if not album.mb_albumid
    ]
    return {"albums": len(albums), "tracks": len(lib.items()), "missing_mb_albumid": missing}
