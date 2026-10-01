"""The commands that the server runs. The names are beets' names."""

from rbeets.commands import import_, mbsync, restrict, stats, version

COMMANDS = {
    "version": version.run,
    "import": import_.run,
    "mbsync": mbsync.run,
    "stats": stats.run,
    "restrict": restrict.run,
}

# Commands that change the database take the root's lock.
LOCKED = {"import", "mbsync"}
