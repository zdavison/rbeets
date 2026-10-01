"""The commands that the server runs."""

from rbeets.commands import hello, index, refresh, restrict, stats

COMMANDS = {
    "hello": hello.run,
    "index": index.run,
    "refresh": refresh.run,
    "stats": stats.run,
    "restrict": restrict.run,
}

# Commands that change the database take the root's lock.
LOCKED = {"index", "refresh"}
