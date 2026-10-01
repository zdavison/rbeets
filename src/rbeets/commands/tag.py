"""import -L: match each album with no MusicBrainz album ID, and tag the
albums that beets matches with confidence.

Each album runs in its own import session over the database, as
`beet import -L` does. One session for each album keeps a MusicBrainz error
to that album, and gives the progress events a total."""

from __future__ import annotations

from collections import Counter

from beets import config
from beets.autotag.match import Recommendation
from beets.importer import Action, ImportSession

from rbeets import subpath
from rbeets.beetsenv import open_library
from rbeets.session import Session
from rbeets.state import backup


class _Matcher(ImportSession):
    """Applies the best candidate only when beets rates it strong. Never asks."""

    def __init__(self, lib, query: str, pretend: bool) -> None:
        super().__init__(lib, None, None, query=query)
        self.pretend = pretend
        self.best = None
        self.strong = False

    def should_resume(self, path: bytes) -> bool:
        return False

    def choose_match(self, task):
        self.best = task.candidates[0] if task.candidates else None
        self.strong = task.rec == Recommendation.strong
        if self.strong and not self.pretend:
            return self.best
        return Action.SKIP

    def choose_item(self, task):
        return Action.SKIP


def _describe(best) -> dict:
    if best is None:
        return {"match": None, "release": None, "distance": None}
    return {
        "match": f"{best.info.artist} - {best.info.album}",
        "release": best.info.album_id,
        "distance": round(float(best.distance), 3),
    }


def import_library(session: Session, folder: str, pretend: bool) -> dict:
    backup(session.state)
    lib = open_library(session.root, session.state)
    config["import"]["autotag"] = True
    albums = [
        album
        for album in lib.albums()
        if not album.mb_albumid and subpath.in_folder(subpath.album_folder(album), folder)
    ]
    outcomes: Counter[str] = Counter()
    for done, album in enumerate(albums, start=1):
        if session.stopped.is_set():
            break
        name = f"{album.albumartist} - {album.album}"
        matcher = _Matcher(lib, f"id:{album.id}", pretend)
        try:
            matcher.run()
        except Exception as exc:
            outcome = "failed"
            session.log("error", f"{name}: {type(exc).__name__}: {exc}")
        else:
            if not matcher.strong:
                outcome = "skipped"
            else:
                outcome = "proposed" if pretend else "tagged"
        outcomes[outcome] += 1
        session.progress(done, len(albums), name, outcome=outcome, **_describe(matcher.best))
    return {
        "tagged": outcomes["tagged"],
        "proposed": outcomes["proposed"],
        "skipped": outcomes["skipped"],
        "failed": outcomes["failed"],
        "stopped": session.stopped.is_set(),
    }
