"""What a command gets from the server."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    root: str
    state: Path
    send: Callable[[dict], None]
    # Set when the client leaves. Commands check it between albums.
    stopped: threading.Event = field(default_factory=threading.Event)
    # True when sshd started the server as a forced command.
    pinned: bool = False
    # The absolute path of the server's own executable, for restrict.
    executable: str = "rbeets"

    def progress(self, done: int, total: int | None, album: str, **extra: str) -> None:
        self.send({"type": "progress", "done": done, "total": total, "album": album, **extra})

    def log(self, level: str, message: str) -> None:
        self.send({"type": "log", "level": level, "message": message})
