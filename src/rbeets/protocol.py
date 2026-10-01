"""Messages and exit codes that the client and the server share."""

from __future__ import annotations

import json

PROTOCOL = 1

OK = 0
USAGE = 1
PROTOCOL_MISMATCH = 2
BAD_ROOT = 3
BUSY = 4
BEETS_FAILED = 5
NOT_ALLOWED = 6
STILL_UNRESTRICTED = 7
SSH_FAILED = 255

# The last event of every command is one of these.
FINAL = ("result", "error")


class ProtocolError(Exception):
    """A line that is not a protocol message."""


class Failure(Exception):
    """A command failed. The server sends it as an error event."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def encode(message: dict) -> bytes:
    return json.dumps(message, separators=(",", ":")).encode() + b"\n"


def decode(line: bytes) -> dict:
    try:
        message = json.loads(line)
    except ValueError as exc:
        raise ProtocolError(f"not JSON: {line[:200]!r}") from exc
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ProtocolError(f"not a message: {line[:200]!r}")
    return message


def error(code: int, message: str) -> dict:
    return {"type": "error", "code": code, "message": message}
