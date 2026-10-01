"""The server end: read the hello, run one command, send events."""

from __future__ import annotations

import os
import sys
import threading
from typing import BinaryIO

from beets import __version__ as beets_version

from rbeets import __version__
from rbeets.commands import COMMANDS, LOCKED
from rbeets.protocol import (
    BAD_ROOT,
    BEETS_FAILED,
    BUSY,
    OK,
    PROTOCOL,
    PROTOCOL_MISMATCH,
    USAGE,
    Failure,
    ProtocolError,
    decode,
    encode,
    error,
)
from rbeets.session import Session
from rbeets.state import Busy, lock, state_dir
from rbeets.target import normalize_root


def protect_stdout() -> BinaryIO:
    """Keep the real standard output for protocol messages. Point file
    descriptor 1 and sys.stdout at standard error, so that a print in beets
    cannot corrupt the protocol."""
    sys.stdout.flush()
    protocol_out = os.fdopen(os.dup(1), "wb", buffering=0)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return protocol_out


def watch(inp: BinaryIO, stopped: threading.Event) -> None:
    """The client sends nothing after hello. End of input means the client left."""
    try:
        while inp.read(4096):
            pass
    except (OSError, ValueError):  # ValueError: the input closed under this thread
        pass
    stopped.set()


def serve(root: str, pinned: bool, inp: BinaryIO, out: BinaryIO, executable: str = "rbeets") -> int:
    stopped = threading.Event()

    def send(message: dict) -> None:
        try:
            out.write(encode(message))
            out.flush()
        except OSError:
            stopped.set()

    def fail(code: int, message: str) -> int:
        send(error(code, message))
        return code

    try:
        hello = decode(inp.readline())
    except ProtocolError as exc:
        return fail(PROTOCOL_MISMATCH, f"expected a hello message: {exc}")
    if hello.get("type") != "hello" or hello.get("protocol") != PROTOCOL:
        return fail(
            PROTOCOL_MISMATCH,
            f"the library host speaks protocol {PROTOCOL} and the client speaks "
            f"{hello.get('protocol')}. Install the same rbeets on both ends: pipx upgrade rbeets",
        )
    try:
        root = normalize_root(root)
        asked = normalize_root(str(hello.get("root", "")))
    except ValueError as exc:
        return fail(BAD_ROOT, str(exc))
    if asked != root:
        return fail(BAD_ROOT, f"this connection works on {root} only, not on {asked}")
    if not os.path.isdir(root):
        return fail(BAD_ROOT, f"{root} is not a folder on the library host")
    command = hello.get("command")
    args = hello.get("args", [])
    if command not in COMMANDS:
        return fail(USAGE, f"unknown command: {command!r}")
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        return fail(USAGE, "args must be a list of strings")

    send({"type": "ready", "protocol": PROTOCOL, "rbeets": __version__, "beets": beets_version})
    threading.Thread(target=watch, args=(inp, stopped), daemon=True).start()
    session = Session(
        root=root,
        state=state_dir(root),
        send=send,
        stopped=stopped,
        pinned=pinned,
        executable=executable,
    )
    try:
        if command in LOCKED:
            with lock(session.state):
                result = COMMANDS[command](session, args)
        else:
            result = COMMANDS[command](session, args)
    except Busy:
        return fail(BUSY, f"another rbeets command is running on {root}")
    except Failure as exc:
        return fail(exc.code, exc.message)
    except Exception as exc:  # beets raises many exception types
        return fail(BEETS_FAILED, f"{type(exc).__name__}: {exc}")
    send({"type": "result", "command": command, **result})
    return OK
