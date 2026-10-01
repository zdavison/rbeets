"""restrict: lock one key in authorized_keys to rbeets on this root."""

from __future__ import annotations

import shlex
from pathlib import Path

from rbeets.authkeys import install, parse_public_key, rewrite
from rbeets.protocol import BAD_ROOT, NOT_ALLOWED, USAGE, Failure
from rbeets.session import Session


def run(session: Session, args: list[str]) -> dict:
    if session.pinned:
        # Otherwise a restricted key could pin itself to another root.
        raise Failure(
            NOT_ALLOWED,
            "this key is restricted already. Edit authorized_keys on the library host to change it",
        )
    if len(args) != 1:
        raise Failure(USAGE, "restrict takes one argument: the public key")
    try:
        key = parse_public_key(args[0])
    except ValueError as exc:
        raise Failure(USAGE, str(exc)) from exc
    path = Path.home() / ".ssh" / "authorized_keys"
    if not path.exists():
        raise Failure(BAD_ROOT, f"{path} does not exist")
    forced = shlex.join([session.executable, "--server", "--root", session.root, "--pinned"])
    install(path, rewrite(path.read_bytes(), key, forced))
    return {"forced_command": forced}
