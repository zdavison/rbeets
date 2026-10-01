"""The client end: start the server over ssh, send hello, read events."""

from __future__ import annotations

import shlex
import subprocess
from collections.abc import Callable

from rbeets import __version__
from rbeets.protocol import (
    FINAL,
    OK,
    PROTOCOL,
    PROTOCOL_MISMATCH,
    STILL_UNRESTRICTED,
    ProtocolError,
    decode,
    encode,
    error,
)
from rbeets.target import Target

Handler = Callable[[dict], None]


def server_command(rbeets_path: str, root: str) -> str:
    # ssh hands the remote command to the remote shell, so quote each word.
    return shlex.join([rbeets_path, "--server", "--root", root])


def run(ssh: str, target: Target, remote: str, command: str, args: list[str], on_event: Handler) -> int:
    argv = [*shlex.split(ssh), target.host, remote]
    hello = {
        "type": "hello",
        "protocol": PROTOCOL,
        "rbeets": __version__,
        "command": command,
        "args": args,
        "root": target.root,
    }
    final = None
    with subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        assert process.stdin and process.stdout
        try:
            process.stdin.write(encode(hello))
            process.stdin.flush()
        except BrokenPipeError:
            pass
        for line in process.stdout:
            try:
                event = decode(line)
            except ProtocolError:
                final = error(PROTOCOL_MISMATCH, f"unexpected output from the library host: {line[:200]!r}")
                on_event(final)
                break
            on_event(event)
            if event["type"] in FINAL:
                final = event
                break
        # Standard input stays open until the last event. Closing it tells the
        # server that the client left.
        process.stdin.close()
        returncode = process.wait()
    if final is None:
        return returncode or PROTOCOL_MISMATCH
    if final["type"] == "result":
        return OK
    return int(final["code"])


def restrict(ssh: str, target: Target, rbeets_path: str, public_key: str, on_event: Handler) -> int:
    code = run(ssh, target, server_command(rbeets_path, target.root), "restrict", [public_key], on_event)
    if code != OK:
        return code
    # Ask for `echo`. A restricted key runs the forced command instead, and the
    # server answers. An unrestricted key runs echo, and the text is not a message.
    check = run(ssh, target, "echo rbeets-unrestricted", "version", [], lambda event: None)
    if check == OK:
        on_event({"type": "log", "level": "info", "message": "the key now runs rbeets only, on this root"})
        return OK
    on_event(
        error(
            STILL_UNRESTRICTED,
            "the connection still runs other commands. If ssh connects with a key "
            "other than the one you restricted, pass that key with -e 'ssh -i KEY'",
        )
    )
    return STILL_UNRESTRICTED
