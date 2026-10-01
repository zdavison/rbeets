import shutil

import pytest

from rbeets.commands import import_
from rbeets.protocol import Failure


def test_index_adds_each_album_once(session, make_album, events):
    make_album("Artist A", "First")
    make_album("Artist B", "Second")
    assert import_.run(session, ["-A"]) == {"albums_added": 2, "albums": 2, "tracks": 4}
    assert [e["done"] for e in events if e["type"] == "progress"] == [1, 2]


def test_progress_names_the_album(session, make_album, events):
    make_album("Artist A", "First")
    import_.run(session, ["-A"])
    assert events[0] == {"type": "progress", "done": 1, "total": None, "album": "Artist A - First"}


def test_a_second_index_adds_nothing(session, make_album):
    make_album("Artist A", "First")
    import_.run(session, ["-A"])
    assert import_.run(session, ["-A"])["albums_added"] == 0


def test_index_leaves_every_file_in_place_and_unchanged(session, make_album, root):
    folder = make_album("Artist A", "First")
    paths = sorted(p.relative_to(root) for p in root.rglob("*"))
    contents = (folder / "01.mp3").read_bytes()
    import_.run(session, ["-A"])
    assert sorted(p.relative_to(root) for p in root.rglob("*")) == paths
    assert (folder / "01.mp3").read_bytes() == contents


def test_index_keeps_both_copies_of_a_duplicate_album(session, make_album, root):
    folder = make_album("Artist A", "First")
    shutil.copytree(folder, root / "Copy" / "First")
    result = import_.run(session, ["-A"])
    assert result["albums"] == 2
    assert len(list(root.rglob("*.mp3"))) == 4


def test_index_backs_up_the_database_before_it_writes(session, make_album):
    make_album("Artist A", "First")
    import_.run(session, ["-A"])
    import_.run(session, ["-A"])
    assert (session.state / "library.db.bak").exists()


def test_index_stops_after_the_current_album(session, make_album):
    make_album("Artist A", "First")
    make_album("Artist B", "Second")
    session.stopped.set()
    assert import_.run(session, ["-A"])["albums_added"] == 1
