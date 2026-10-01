"""Read and rewrite ~/.ssh/authorized_keys, as sshd reads it (sshd(8), AUTHORIZED_KEYS FILE FORMAT)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from rbeets.protocol import BAD_ROOT, Failure

KEY_TYPES = {
    "ssh-ed25519",
    "ssh-rsa",
    "ssh-dss",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "sk-ssh-ed25519@openssh.com",
    "sk-ecdsa-sha2-nistp256@openssh.com",
}


@dataclass(frozen=True)
class PublicKey:
    type: str
    data: str


def _options_end(text: str) -> int:
    """The index of the first space outside double quotes."""
    quoted = False
    i = 0
    while i < len(text):
        char = text[i]
        if quoted and char == "\\":
            i += 2
            continue
        if char == '"':
            quoted = not quoted
        elif char in " \t" and not quoted:
            return i
        i += 1
    return len(text)


def _split_options(options: str) -> list[str]:
    """Split options at commas outside double quotes."""
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    i = 0
    while i < len(options):
        char = options[i]
        if quoted and char == "\\" and i + 1 < len(options):
            current.append(options[i : i + 2])
            i += 2
            continue
        if char == '"':
            quoted = not quoted
        if char == "," and not quoted:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
        i += 1
    parts.append("".join(current))
    return [part for part in parts if part]


def split_line(line: str) -> tuple[str, PublicKey, str] | None:
    """Split one line into options, key and comment. None for a blank line, a
    comment, or a line with no key."""
    text = line.strip()
    if not text or text.startswith("#"):
        return None
    options = ""
    if text.split(None, 1)[0] not in KEY_TYPES:
        end = _options_end(text)
        options, text = text[:end], text[end:].lstrip()
    fields = text.split(None, 2)
    if len(fields) < 2 or fields[0] not in KEY_TYPES:
        return None
    comment = fields[2] if len(fields) == 3 else ""
    return options, PublicKey(fields[0], fields[1]), comment


def parse_public_key(text: str) -> PublicKey:
    parts = split_line(text)
    if parts is None or parts[0]:
        raise ValueError("not an SSH public key")
    return parts[1]


def _matches(raw: bytes, key: PublicKey) -> bool:
    parts = split_line(raw.decode("latin-1"))
    return parts is not None and parts[1] == key


def rewrite(content: bytes, key: PublicKey, forced_command: str) -> bytes:
    lines = content.splitlines(keepends=True)
    matches = [i for i, raw in enumerate(lines) if _matches(raw, key)]
    if not matches:
        raise Failure(BAD_ROOT, "no line in authorized_keys has this key")
    if len(matches) > 1:
        raise Failure(BAD_ROOT, f"{len(matches)} lines in authorized_keys have this key. Leave one")
    i = matches[0]
    raw = lines[i]
    body = raw.rstrip(b"\r\n")
    ending = raw[len(body) :]
    _, found, comment = split_line(body.decode("latin-1"))
    # sshd reads \" inside a quoted option as a quote, and nothing else as an escape.
    escaped = forced_command.replace('"', '\\"')
    restricted = f'restrict,command="{escaped}" {found.type} {found.data}'
    if comment:
        restricted += f" {comment}"
    lines[i] = restricted.encode("latin-1") + ending
    return b"".join(lines)


def forced_command_for(content: bytes, key: PublicKey) -> str | None:
    for raw in content.splitlines():
        parts = split_line(raw.decode("latin-1"))
        if parts is None or parts[1] != key:
            continue
        for option in _split_options(parts[0]):
            if option.startswith('command="') and option.endswith('"'):
                return option[len('command="') : -1].replace('\\"', '"')
        return None
    return None


def install(path: Path, content: bytes) -> None:
    """Replace PATH in one rename, with mode 600."""
    temporary = path.with_name(path.name + ".rbeets-tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
