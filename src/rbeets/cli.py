"""rbeets [OPTIONS] HOST:ROOT COMMAND [ARGS], and rbeets --server on the library host."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from rbeets import client
from rbeets.output import human_handler, json_handler
from rbeets.protocol import USAGE
from rbeets.target import parse_target

COMMAND_NAMES = ["version", "import", "mbsync", "stats", "restrict"]


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        # argparse exits with 2, and 2 means a protocol mismatch in rbeets.
        self.print_usage(sys.stderr)
        self.exit(USAGE, f"{self.prog}: error: {message}\n")


def main(argv: list[str] | None = None) -> None:
    sys.exit(run(sys.argv[1:] if argv is None else argv))


def run(argv: list[str]) -> int:
    if argv[:1] == ["--server"]:
        return _server(argv[1:])
    parser = _Parser(prog="rbeets", description="Run beets on a remote host over SSH.")
    parser.add_argument("-e", dest="ssh", default="ssh", metavar="COMMAND", help="the SSH command (default: ssh)")
    parser.add_argument(
        "--rbeets-path", default="rbeets", metavar="PATH", help="the path of rbeets on the library host"
    )
    parser.add_argument("--json", action="store_true", help="print each event as one JSON line")
    parser.add_argument("target", metavar="HOST:ROOT")
    parser.add_argument("command", choices=COMMAND_NAMES)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    opts = parser.parse_args(argv)
    try:
        target = parse_target(opts.target)
    except ValueError as exc:
        parser.error(str(exc))
    on_event = json_handler if opts.json else human_handler
    if opts.command == "restrict":
        if len(opts.args) != 1:
            parser.error("restrict takes one argument: KEY.pub")
        try:
            public_key = Path(opts.args[0]).read_text().strip()
        except OSError as exc:
            parser.error(f"cannot read {opts.args[0]}: {exc.strerror}")
        return client.restrict(opts.ssh, target, opts.rbeets_path, public_key, on_event)
    remote = client.server_command(opts.rbeets_path, target.root)
    return client.run(opts.ssh, target, remote, opts.command, opts.args, on_event)


def _server(argv: list[str]) -> int:
    parser = _Parser(prog="rbeets --server")
    parser.add_argument("--root", required=True)
    parser.add_argument("--pinned", action="store_true")
    opts = parser.parse_args(argv)
    # Import the server here, so that the client never imports beets.
    from rbeets.server import protect_stdout, serve

    out = protect_stdout()
    code = serve(opts.root, opts.pinned, sys.stdin.buffer, out, executable=os.path.abspath(sys.argv[0]))
    # The thread that watches standard input still holds the stdin lock, and a
    # normal interpreter shutdown aborts on that lock. Every event is sent, so
    # flush and leave without the shutdown.
    sys.stderr.flush()
    os._exit(code)
