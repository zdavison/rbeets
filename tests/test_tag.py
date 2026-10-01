import uuid

import pytest
from beets.autotag import AlbumInfo, TrackInfo
from mediafile import MediaFile

from rbeets.beetsenv import open_library
from rbeets.commands import import_

RELEASE = "11111111-1111-4111-8111-111111111111"
KNOWN = "22222222-2222-4222-8222-222222222222"


def release(artist: str, album: str, titles: list[str], release_id: str, length: float = 0.1) -> AlbumInfo:
    return AlbumInfo(
        tracks=[
            TrackInfo(
                title=title,
                track_id=str(uuid.uuid4()),
                index=n,
                medium=1,
                medium_index=n,
                artist=artist,
                length=length,
            )
            for n, title in enumerate(titles, start=1)
        ],
        album=album,
        album_id=release_id,
        artist=artist,
        artist_id=str(uuid.uuid4()),
        data_source="MusicBrainz",
    )


CLOSE = release("Artist A", "First", ["Track 1", "Track 2"], RELEASE)
DISTANT = release("Zed", "Unrelated", ["Something Else"], RELEASE, length=300)


@pytest.fixture
def musicbrainz(monkeypatch):
    """Replace the MusicBrainz search. RELEASES maps an album name to the
    releases the search returns. FAILING names albums whose search raises."""

    class Source:
        releases: dict[str, list[AlbumInfo]] = {}
        failing: set[str] = set()
        searched: list[str] = []

    def candidates(items, *args, **kwargs):
        album = items[0].album
        Source.searched.append(album)
        if album in Source.failing:
            raise ConnectionError("MusicBrainz did not answer")
        yield from Source.releases.get(album, [])

    Source.releases, Source.failing, Source.searched = {}, set(), []
    monkeypatch.setattr("beets.metadata_plugins.candidates", candidates)
    return Source


def test_a_close_match_is_tagged_in_place(session, make_album, musicbrainz, root):
    folder = make_album("Artist A", "First")
    import_.run(session, ["-A"])
    paths = sorted(p.relative_to(root) for p in root.rglob("*"))
    musicbrainz.releases = {"First": [CLOSE]}
    assert import_.run(session, ["-L"])["tagged"] == 1
    assert MediaFile(folder / "01.mp3").mb_albumid == RELEASE
    assert sorted(p.relative_to(root) for p in root.rglob("*")) == paths


def test_a_distant_match_is_skipped(session, make_album, musicbrainz):
    folder = make_album("Artist A", "First")
    import_.run(session, ["-A"])
    contents = (folder / "01.mp3").read_bytes()
    musicbrainz.releases = {"First": [DISTANT]}
    assert import_.run(session, ["-L"])["skipped"] == 1
    assert (folder / "01.mp3").read_bytes() == contents


def test_pretend_writes_nothing(session, make_album, musicbrainz):
    folder = make_album("Artist A", "First")
    import_.run(session, ["-A"])
    contents = (folder / "01.mp3").read_bytes()
    musicbrainz.releases = {"First": [CLOSE]}
    assert import_.run(session, ["-L", "--pretend"])["proposed"] == 1
    assert (folder / "01.mp3").read_bytes() == contents
    assert open_library(session.root, session.state).albums().get().mb_albumid == ""


def test_progress_names_the_best_candidate(session, make_album, musicbrainz, events):
    make_album("Artist A", "First")
    import_.run(session, ["-A"])
    events.clear()
    musicbrainz.releases = {"First": [CLOSE]}
    import_.run(session, ["-L"])
    assert [e for e in events if e["type"] == "progress"] == [
        {
            "type": "progress",
            "done": 1,
            "total": 1,
            "album": "Artist A - First",
            "outcome": "tagged",
            "match": "Artist A - First",
            "release": RELEASE,
            "distance": 0.0,
        }
    ]


def test_an_album_with_no_candidate_is_skipped_with_no_match(session, make_album, musicbrainz, events):
    make_album("Artist A", "First")
    import_.run(session, ["-A"])
    events.clear()
    assert import_.run(session, ["-L"])["skipped"] == 1
    progress = [e for e in events if e["type"] == "progress"][0]
    assert (progress["match"], progress["release"], progress["distance"]) == (None, None, None)


def test_a_lookup_error_fails_one_album_and_continues(session, make_album, musicbrainz, events):
    make_album("Artist A", "First")
    make_album("Artist A", "Second", tracks=2)
    import_.run(session, ["-A"])
    musicbrainz.failing = {"First"}
    musicbrainz.releases = {"Second": [release("Artist A", "Second", ["Track 1", "Track 2"], RELEASE)]}
    result = import_.run(session, ["-L"])
    assert (result["failed"], result["tagged"]) == (1, 1)
    logs = [e["message"] for e in events if e["type"] == "log"]
    assert any("Artist A - First" in m and "MusicBrainz did not answer" in m for m in logs)


def test_albums_with_an_id_are_left_out(session, make_album, musicbrainz):
    make_album("Artist A", "First", mb_albumid=KNOWN)
    import_.run(session, ["-A"])
    result = import_.run(session, ["-L"])
    assert result == {"tagged": 0, "proposed": 0, "skipped": 0, "failed": 0, "stopped": False}
    assert musicbrainz.searched == []


def test_a_subpath_limits_the_albums(session, make_album, musicbrainz):
    make_album("Artist A", "First")
    make_album("Artist B", "Second")
    import_.run(session, ["-A"])
    import_.run(session, ["-L", "Artist A"])
    assert musicbrainz.searched == ["First"]


def test_a_second_run_leaves_tagged_albums_out(session, make_album, musicbrainz):
    make_album("Artist A", "First")
    import_.run(session, ["-A"])
    musicbrainz.releases = {"First": [CLOSE]}
    import_.run(session, ["-L"])
    musicbrainz.searched.clear()
    import_.run(session, ["-L"])
    assert musicbrainz.searched == []


def test_import_l_stops_before_the_next_album(session, make_album, musicbrainz):
    make_album("Artist A", "First")
    import_.run(session, ["-A"])
    session.stopped.set()
    assert import_.run(session, ["-L"])["stopped"] is True
    assert musicbrainz.searched == []
