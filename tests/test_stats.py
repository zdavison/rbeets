import pytest

from rbeets.commands import index, stats
from rbeets.protocol import Failure

ALBUM_ID = "11111111-1111-4111-8111-111111111111"


def test_stats_counts_albums_and_tracks(session, make_album):
    make_album("Artist A", "First", tracks=3, mb_albumid=ALBUM_ID)
    make_album("Artist B", "Second")
    index.run(session, [])
    result = stats.run(session, [])
    assert (result["albums"], result["tracks"]) == (2, 5)


def test_stats_lists_albums_without_a_musicbrainz_id(session, make_album):
    make_album("Artist A", "First", mb_albumid=ALBUM_ID)
    folder = make_album("Artist B", "Second")
    index.run(session, [])
    assert stats.run(session, [])["missing_mb_albumid"] == [
        {"albumartist": "Artist B", "album": "Second", "path": str(folder)}
    ]


def test_stats_before_index_reports_an_empty_library(session):
    assert stats.run(session, []) == {"albums": 0, "tracks": 0, "missing_mb_albumid": []}


def test_stats_does_not_back_up_the_database(session, make_album):
    make_album("Artist A", "First")
    index.run(session, [])
    (session.state / "library.db.bak").unlink(missing_ok=True)
    stats.run(session, [])
    assert not (session.state / "library.db.bak").exists()


def test_stats_takes_no_arguments(session):
    with pytest.raises(Failure):
        stats.run(session, ["extra"])
