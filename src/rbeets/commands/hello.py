"""hello: report the versions of the server."""

from __future__ import annotations

from beets import __version__ as beets_version

from rbeets import __version__
from rbeets.protocol import PROTOCOL, USAGE, Failure
from rbeets.session import Session


def run(session: Session, args: list[str]) -> dict:
    if args:
        raise Failure(USAGE, "hello takes no arguments")
    return {
        "protocol": PROTOCOL,
        "rbeets": __version__,
        "beets": beets_version,
        "root": session.root,
        "state": str(session.state),
    }
