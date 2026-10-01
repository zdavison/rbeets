import shutil

import pytest

from rbeets.commands import index
from rbeets.protocol import Failure


def test_index_adds_each_album_once(session, make_album, events):
    make_album("Artist A", "First")
    make_album("Artist B", "Second")
    assert index.run(session, []) == {"albums_added": 2, "albums": 2, "tracks": 4}
    assert [e["done"] for e in events if e["type"] == "progress"] == [1, 2]


def test_progress_names_the_album(session, make_album, events):
    make_album("Artist A", "First")
    index.run(session, [])
    assert events[0] == {"type": "progress", "done": 1, "total": None, "album": "Artist A - First"}


def test_a_second_index_adds_nothing(session, make_album):
    make_album("Artist A", "First")
    index.run(session, [])
    assert index.run(session, [])["albums_added"] == 0


def test_index_leaves_every_file_in_place_and_unchanged(session, make_album, root):
    folder = make_album("Artist A", "First")
    paths = sorted(p.relative_to(root) for p in root.rglob("*"))
    contents = (folder / "01.mp3").read_bytes()
    index.run(session, [])
    assert sorted(p.relative_to(root) for p in root.rglob("*")) == paths
    assert (folder / "01.mp3").read_bytes() == contents


def test_index_keeps_both_copies_of_a_duplicate_album(session, make_album, root):
    folder = make_album("Artist A", "First")
    shutil.copytree(folder, root / "Copy" / "First")
    result = index.run(session, [])
    assert result["albums"] == 2
    assert len(list(root.rglob("*.mp3"))) == 4


def test_index_backs_up_the_database_before_it_writes(session, make_album):
    make_album("Artist A", "First")
    index.run(session, [])
    index.run(session, [])
    assert (session.state / "library.db.bak").exists()


def test_index_stops_after_the_current_album(session, make_album):
    make_album("Artist A", "First")
    make_album("Artist B", "Second")
    session.stopped.set()
    assert index.run(session, [])["albums_added"] == 1


def test_index_takes_no_arguments(session):
    with pytest.raises(Failure) as caught:
        index.run(session, ["extra"])
    assert caught.value.code == 1
