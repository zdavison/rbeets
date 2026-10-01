"""import: -A adds albums to the database as they are. -L matches albums
against MusicBrainz and tags the confident matches."""

from __future__ import annotations

from rbeets import subpath
from rbeets.commands import _args, index, tag
from rbeets.protocol import USAGE, Failure
from rbeets.session import Session


def run(session: Session, args: list[str]) -> dict:
    flags, paths = _args.parse("import", args, {"-A", "-L", "--pretend"}, 1)
    modes = flags & {"-A", "-L"}
    if len(modes) != 1:
        raise Failure(USAGE, "import needs exactly one of -A and -L")
    if "-A" in modes and "--pretend" in flags:
        raise Failure(USAGE, "--pretend works with import -L only")
    folder = subpath.resolve(session.root, paths[0] if paths else None)
    if "-A" in modes:
        return index.import_as_is(session, folder)
    return tag.import_library(session, folder, pretend="--pretend" in flags)
