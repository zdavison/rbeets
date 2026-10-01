import hashlib
from pathlib import Path

import pytest

from rbeets.state import Busy, backup, lock, state_dir


def test_state_dir_uses_xdg_data_home():
    digest = hashlib.sha256(b"/music").hexdigest()[:16]
    assert state_dir("/music", {"XDG_DATA_HOME": "/data"}) == Path("/data/rbeets", digest)


def test_state_dir_falls_back_to_local_share(isolated_home):
    assert state_dir("/music", {}).parent == isolated_home / ".local/share/rbeets"


def test_each_root_gets_its_own_state_dir():
    assert state_dir("/a", {"XDG_DATA_HOME": "/d"}) != state_dir("/b", {"XDG_DATA_HOME": "/d"})


def test_a_second_lock_on_one_state_dir_is_busy(tmp_path):
    with lock(tmp_path / "state"):
        with pytest.raises(Busy):
            with lock(tmp_path / "state"):
                pass


def test_the_lock_is_free_again_after_the_block(tmp_path):
    with lock(tmp_path / "state"):
        pass
    with lock(tmp_path / "state"):
        pass


def test_backup_copies_the_database(tmp_path):
    (tmp_path / "library.db").write_bytes(b"db")
    backup(tmp_path)
    assert (tmp_path / "library.db.bak").read_bytes() == b"db"


def test_backup_without_a_database_does_nothing(tmp_path):
    backup(tmp_path)
    assert not (tmp_path / "library.db.bak").exists()
