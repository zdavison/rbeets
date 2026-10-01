"""The beets configuration that every command runs under."""

from __future__ import annotations

import os
from pathlib import Path

from beets import config, library, plugins


def open_library(root: str, state: Path) -> library.Library:
    state.mkdir(parents=True, exist_ok=True)
    # beets reads its config file from BEETSDIR. Pointing it at the state
    # folder, and reading no user file, keeps the owner's beets setup out.
    os.environ["BEETSDIR"] = str(state)
    config.clear()
    config.read(user=False, defaults=True)
    config.set(
        {
            "directory": root,
            "library": str(state / "library.db"),
            "plugins": ["musicbrainz"],
            "threaded": False,
            # Let a MusicBrainz error reach refresh, which reports the reason.
            "raise_on_error": True,
            "import": {
                "move": False,
                "copy": False,
                "link": False,
                "hardlink": False,
                "reflink": False,
                "write": True,
                "autotag": False,
                "quiet": True,
                "incremental": True,
                "resume": False,
                "log": None,
                # "remove" deletes files. Keep both copies of a duplicate album.
                "duplicate_action": "keep",
            },
        }
    )
    # beets loads plugins once for each process. Clear them so that the
    # configuration above decides which plugins load.
    plugins._instances.clear()
    plugins.load_plugins()
    return library.Library(str(state / "library.db"), root)
