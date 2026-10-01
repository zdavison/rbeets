"""HOST:ROOT, as rsync writes it."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    host: str
    root: str


def normalize_root(root: str) -> str:
    """One spelling for each root, so that /music/ and /music share a state folder."""
    if not root.startswith("/"):
        raise ValueError(f"the root must be an absolute path: {root!r}")
    return posixpath.normpath(root)


def parse_target(text: str) -> Target:
    host, colon, root = text.partition(":")
    if not colon or not host:
        raise ValueError(f"expected HOST:ROOT, got {text!r}")
    return Target(host, normalize_root(root))
