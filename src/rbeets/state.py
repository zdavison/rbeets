"""The state folder of each root: database, lock and backup."""

from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path


class Busy(Exception):
    """Another command holds the lock for this root."""


def state_dir(root: str, env: Mapping[str, str] = os.environ) -> Path:
    base = env.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    digest = hashlib.sha256(root.encode()).hexdigest()[:16]
    return Path(base, "rbeets", digest)


@contextmanager
def lock(state: Path) -> Iterator[None]:
    state.mkdir(parents=True, exist_ok=True)
    with open(state / "lock", "w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Busy(str(state)) from exc
        yield


def backup(state: Path) -> None:
    """Keep one copy of the database from before the command."""
    database = state / "library.db"
    if database.exists():
        shutil.copy2(database, state / "library.db.bak")
