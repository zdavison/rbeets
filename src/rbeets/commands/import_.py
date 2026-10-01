"""import: -A adds albums to the database as they are."""

from __future__ import annotations

from rbeets.commands import _args, index
from rbeets.protocol import USAGE, Failure
from rbeets.session import Session


def run(session: Session, args: list[str]) -> dict:
    flags, _paths = _args.parse("import", args, {"-A"}, 1)
    if "-A" not in flags:
        raise Failure(USAGE, "import needs -A")
    return index.import_as_is(session, session.root)
