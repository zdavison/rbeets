from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from mediafile import MediaFile

from rbeets.session import Session
from rbeets.state import state_dir

SILENT = Path(__file__).parent / "fixtures" / "silent.mp3"


def track_id(album_id: str, number: int) -> str:
    """The MusicBrainz recording ID that the fixtures give track NUMBER of an album."""
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"{album_id}/{number}"))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Keep every test away from the real home folder and the real state folder."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return home


@pytest.fixture
def root(tmp_path) -> Path:
    path = tmp_path / "music"
    path.mkdir()
    return path


@pytest.fixture
def make_album(root):
    def make(artist: str, album: str, tracks: int = 2, mb_albumid: str | None = None) -> Path:
        folder = root / artist / album
        folder.mkdir(parents=True)
        for number in range(1, tracks + 1):
            path = folder / f"{number:02}.mp3"
            shutil.copy(SILENT, path)
            tags = MediaFile(path)
            tags.artist = artist
            tags.albumartist = artist
            tags.album = album
            tags.title = f"Track {number}"
            tags.track = number
            tags.disc = 1
            if mb_albumid:
                tags.mb_albumid = mb_albumid
                tags.mb_trackid = track_id(mb_albumid, number)
            tags.save()
        return folder

    return make


@pytest.fixture
def events() -> list[dict]:
    return []


@pytest.fixture
def session(root, events) -> Session:
    return Session(root=str(root), state=state_dir(str(root)), send=events.append)
