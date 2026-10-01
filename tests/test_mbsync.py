import pytest
from beets.autotag import AlbumInfo, TrackInfo
from conftest import track_id
from mediafile import MediaFile

from rbeets.commands import import_, mbsync
from rbeets.protocol import Failure

FIRST = "11111111-1111-4111-8111-111111111111"
SECOND = "22222222-2222-4222-8222-222222222222"


def release(album_id: str, tracks: int = 2) -> AlbumInfo:
    return AlbumInfo(
        tracks=[
            TrackInfo(
                title=f"Fixed {n}",
                track_id=track_id(album_id, n),
                index=n,
                medium=1,
                medium_index=n,
                artist="Artist A",
            )
            for n in range(1, tracks + 1)
        ],
        album="Fixed Album",
        album_id=album_id,
        artist="Artist A",
        artist_id="33333333-3333-4333-8333-333333333333",
    )


def lookup(album_id: str, data_source: str) -> AlbumInfo:
    return release(album_id)


def no_lookup(album_id: str, data_source: str) -> AlbumInfo:
    raise AssertionError("refresh looked up an album with no MusicBrainz ID")


def test_refresh_writes_the_new_tags_into_the_files(session, make_album):
    folder = make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    assert mbsync.run(session, [], lookup=lookup)["updated"] == 1
    tags = MediaFile(folder / "01.mp3")
    assert (tags.title, tags.album) == ("Fixed 1", "Fixed Album")


def test_refresh_moves_and_renames_nothing(session, make_album, root):
    make_album("Artist A", "First", mb_albumid=FIRST)
    paths = sorted(p.relative_to(root) for p in root.rglob("*"))
    import_.run(session, ["-A"])
    mbsync.run(session, [], lookup=lookup)
    assert sorted(p.relative_to(root) for p in root.rglob("*")) == paths


def test_a_second_refresh_changes_nothing(session, make_album):
    make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    mbsync.run(session, [], lookup=lookup)
    result = mbsync.run(session, [], lookup=lookup)
    assert (result["unchanged"], result["updated"], result["read"]) == (1, 0, 0)


def test_an_album_without_an_id_is_skipped(session, make_album):
    make_album("Artist B", "Second")
    import_.run(session, ["-A"])
    assert mbsync.run(session, [], lookup=no_lookup)["skipped"] == 1


def test_a_release_that_musicbrainz_does_not_know_fails(session, make_album):
    make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    assert mbsync.run(session, [], lookup=lambda album_id, source: None)["failed"] == 1


def test_a_lookup_error_fails_one_album_and_continues(session, make_album, events):
    make_album("Artist A", "First", mb_albumid=FIRST)
    make_album("Artist B", "Second", mb_albumid=SECOND)
    import_.run(session, ["-A"])

    def flaky(album_id: str, data_source: str) -> AlbumInfo:
        if album_id == FIRST:
            raise ConnectionError("MusicBrainz did not answer")
        return release(album_id)

    result = mbsync.run(session, [], lookup=flaky)
    assert (result["failed"], result["updated"]) == (1, 1)
    logs = [e["message"] for e in events if e["type"] == "log"]
    assert any("Artist A - First" in m and "MusicBrainz did not answer" in m for m in logs)


def test_progress_reports_each_outcome(session, make_album, events):
    make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    events.clear()
    mbsync.run(session, [], lookup=lookup)
    assert [e for e in events if e["type"] == "progress"] == [
        {"type": "progress", "done": 1, "total": 1, "album": "Artist A - First", "outcome": "updated"}
    ]


def test_refresh_stops_before_the_next_album(session, make_album):
    make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    session.stopped.set()
    result = mbsync.run(session, [], lookup=no_lookup)
    assert result["stopped"] is True
    assert result["updated"] + result["unchanged"] + result["failed"] == 0


def test_refresh_backs_up_the_database(session, make_album):
    make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    (session.state / "library.db.bak").unlink(missing_ok=True)
    mbsync.run(session, [], lookup=lookup)
    assert (session.state / "library.db.bak").exists()


def test_refresh_takes_no_arguments(session):
    with pytest.raises(Failure):
        mbsync.run(session, ["extra"], lookup=lookup)


def edit_tags(path, **tags) -> None:
    """Change tags in a file as another tagger would, with a newer modification time."""
    import os

    edited = MediaFile(path)
    for name, value in tags.items():
        setattr(edited, name, value)
    edited.save()
    later = os.stat(path).st_mtime + 10
    os.utime(path, (later, later))


def test_refresh_keeps_a_tag_edit_on_an_album_without_an_id(session, make_album):
    folder = make_album("Artist B", "Second")
    import_.run(session, ["-A"])
    edit_tags(folder / "01.mp3", title="Edited Title")
    mbsync.run(session, [], lookup=no_lookup)
    assert MediaFile(folder / "01.mp3").title == "Edited Title"


def test_refresh_keeps_an_edit_to_a_field_musicbrainz_does_not_set(session, make_album):
    folder = make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    edit_tags(folder / "01.mp3", comments="kept")
    mbsync.run(session, [], lookup=lookup)
    assert MediaFile(folder / "01.mp3").comments == "kept"


def test_refresh_looks_up_a_musicbrainz_id_changed_in_the_files(session, make_album):
    folder = make_album("Artist A", "First", mb_albumid=FIRST)
    import_.run(session, ["-A"])
    for number, path in enumerate(sorted(folder.glob("*.mp3")), start=1):
        edit_tags(path, mb_albumid=SECOND, mb_trackid=track_id(SECOND, number))
    asked = []
    mbsync.run(session, [], lookup=lambda album_id, source: asked.append(album_id) or release(album_id))
    assert asked == [SECOND]
