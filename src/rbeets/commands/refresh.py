"""refresh: read changed files into the database, then sync each album with MusicBrainz.

The read step does what `beet update` does, without moves. Without it, a tag
edit made in another tagger stays only in the file, and the sync writes the
older database values over it.

The beets mbsync plugin does the sync steps, but it reports no outcome for each
album and it prints its changes to standard output. So rbeets runs the steps
itself. match_tracks copies the track matching from beetsplug/mbsync.py.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable

from beets import library, metadata_plugins
from beets.autotag import AlbumInfo, AlbumMatch, Distance, TrackInfo

from rbeets.beetsenv import open_library
from rbeets.protocol import USAGE, Failure
from rbeets.session import Session
from rbeets.state import backup

Lookup = Callable[[str, str], "AlbumInfo | None"]


def default_lookup(album_id: str, data_source: str) -> AlbumInfo | None:
    return metadata_plugins.album_for_id(album_id, data_source)


def match_tracks(items: list[library.Item], info: AlbumInfo) -> dict[library.Item, TrackInfo]:
    by_release_track = {track.release_track_id: track for track in info.tracks}
    by_recording: dict[str, list[TrackInfo]] = defaultdict(list)
    for track in info.tracks:
        by_recording[track.track_id].append(track)
    pairs = {}
    for item in items:
        if item.mb_releasetrackid and item.mb_releasetrackid in by_release_track:
            pairs[item] = by_release_track[item.mb_releasetrackid]
            continue
        candidates = by_recording[item.mb_trackid]
        if len(candidates) == 1:
            pairs[item] = candidates[0]
            continue
        # A recording can appear twice on a release. Disc and track number decide.
        for candidate in candidates:
            if candidate.medium_index == item.track and candidate.medium == item.disc:
                pairs[item] = candidate
                break
    return pairs


def sync_album(lib: library.Library, album: library.Album, lookup: Lookup) -> str:
    if not album.mb_albumid:
        return "skipped"
    items = list(album.items())
    data_source = album.get("data_source") or items[0].get("data_source", "MusicBrainz")
    info = lookup(album.mb_albumid, data_source)
    if info is None:
        return "failed"
    before = [dict(item) for item in items]
    with lib.transaction():
        AlbumMatch(Distance(), info, match_tracks(items, info)).apply_metadata(from_scratch=False)
        changed = [item for item, old in zip(items, before) if dict(item) != old]
        written = [item.try_write() for item in changed]
        for item in changed:
            item.store()
        if changed:
            for key in library.Album.item_keys:
                album[key] = changed[0][key]
            album.store()
    if not all(written):
        return "failed"
    return "updated" if changed else "unchanged"


def read_changed(lib: library.Library) -> int:
    """Read each file that changed since beets last read it, as `beet update`
    does. Returns the number of files read."""
    read = 0
    albums = set()
    for item in lib.items():
        try:
            if item.current_mtime() <= item.mtime:
                continue
            item.read()
        except (OSError, library.ReadError):
            continue  # A missing or unreadable file keeps its database values.
        item.store()
        albums.add(item.album_id)
        read += 1
    for album_id in albums - {None}:
        album = lib.get_album(album_id)
        first = album.items().get() if album else None
        if first is None:
            continue
        for key in library.Album.item_keys:
            album[key] = first[key]
        album.store()
    return read


def run(session: Session, args: list[str], lookup: Lookup = default_lookup) -> dict:
    if args:
        raise Failure(USAGE, "refresh takes no arguments")
    backup(session.state)
    lib = open_library(session.root, session.state)
    read = read_changed(lib)
    albums = list(lib.albums())
    outcomes: Counter[str] = Counter()
    for done, album in enumerate(albums, start=1):
        if session.stopped.is_set():
            break
        name = f"{album.albumartist} - {album.album}"
        try:
            outcome = sync_album(lib, album, lookup)
        except Exception as exc:
            outcome = "failed"
            session.log("error", f"{name}: {type(exc).__name__}: {exc}")
        outcomes[outcome] += 1
        session.progress(done, len(albums), name, outcome=outcome)
    stopped = session.stopped.is_set()
    return {
        "updated": outcomes["updated"],
        "unchanged": outcomes["unchanged"],
        "skipped": outcomes["skipped"],
        "failed": outcomes["failed"],
        "read": read,
        "stopped": stopped,
    }
