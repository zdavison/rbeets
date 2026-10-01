import os

import pytest

from rbeets import subpath
from rbeets.commands import import_, stats
from rbeets.protocol import Failure


def test_no_subpath_names_the_root(root):
    assert subpath.resolve(str(root), None) == str(root)


def test_a_subpath_names_a_folder_in_the_root(root):
    (root / "months" / "2026_08").mkdir(parents=True)
    assert subpath.resolve(str(root), "months/2026_08") == str(root / "months" / "2026_08")


@pytest.mark.parametrize("outside", ["..", "../music-other", "/etc", "months/../.."])
def test_a_subpath_outside_the_root_exits_3(root, outside):
    (root / "months").mkdir()
    with pytest.raises(Failure) as caught:
        subpath.resolve(str(root), outside)
    assert caught.value.code == 3


def test_a_symlink_out_of_the_root_exits_3(root, tmp_path):
    (tmp_path / "elsewhere").mkdir()
    os.symlink(tmp_path / "elsewhere", root / "link")
    with pytest.raises(Failure) as caught:
        subpath.resolve(str(root), "link")
    assert caught.value.code == 3


def test_a_missing_folder_exits_3(root):
    with pytest.raises(Failure) as caught:
        subpath.resolve(str(root), "missing")
    assert caught.value.code == 3


def test_a_root_behind_a_symlink_keeps_its_own_paths(tmp_path):
    real = tmp_path / "real"
    (real / "months").mkdir(parents=True)
    os.symlink(real, tmp_path / "linked")
    assert subpath.resolve(str(tmp_path / "linked"), "months") == str(tmp_path / "linked" / "months")


def test_in_folder_matches_the_folder_and_below_only():
    assert subpath.in_folder("/music/a", "/music/a")
    assert subpath.in_folder("/music/a/b", "/music/a")
    assert not subpath.in_folder("/music/ab", "/music/a")


def test_import_a_with_a_subpath_adds_only_that_folder(session, make_album):
    make_album("Artist A", "First")
    make_album("Artist B", "Second")
    assert import_.run(session, ["-A", "Artist A"])["albums"] == 1


def test_stats_still_lists_album_folders(session, make_album):
    folder = make_album("Artist B", "Second")
    import_.run(session, ["-A"])
    assert stats.run(session, [])["missing_mb_albumid"][0]["path"] == str(folder)
