# rbeets

rbeets runs beets on a remote host over SSH. It works the way rsync works.
You run `rbeets` on your own machine. It connects over SSH and starts
`rbeets --server` on the library host, the machine that holds the music.

rbeets never moves, copies or renames a music file.

## Install

Install rbeets on both machines:

```
pipx install rbeets
```

On the library host, beets installs with rbeets.

## Use

```
rbeets [OPTIONS] HOST:ROOT COMMAND
```

| Command | What it does |
|---|---|
| `hello` | Shows the rbeets, beets and protocol versions on the library host |
| `index` | Adds the music under ROOT to the database, with the tags it has now |
| `refresh` | Updates the tags of each album that has a MusicBrainz album ID |
| `stats` | Counts albums and tracks, and lists albums with no MusicBrainz album ID |
| `restrict KEY.pub` | Locks KEY.pub on the library host to rbeets on ROOT |

Options:

- `-e COMMAND`: the SSH command, as in `rsync -e`. For example `-e "ssh -i ~/.ssh/rbeets"`.
- `--rbeets-path PATH`: the path of rbeets on the library host. Use it if `hello` reports `rbeets: command not found`. pipx installs rbeets in `~/.local/bin`, so pass `--rbeets-path .local/bin/rbeets`. ssh starts in the home folder, so a relative path works. Do not write `~`: rbeets quotes the path, and the library host does not expand a quoted `~`.
- `--json`: print each event as one JSON line.

## Restrict a key

Do these steps once for each key that a program uses:

1. Add the public key to `~/.ssh/authorized_keys` on the library host, with no options.
2. Run `rbeets -e "ssh -i KEY" HOST:ROOT restrict KEY.pub`.

The key then runs `rbeets --server` on ROOT only. To give the key full
access again, edit its line in `~/.ssh/authorized_keys`.

**Warning:** Do not restrict the key that you use to log in. You lose shell
access through that key.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Usage error |
| 2 | The two ends speak different protocol versions |
| 3 | ROOT is missing, the key is pinned to another root, or `restrict` found no single key line |
| 4 | Another rbeets command runs on this root |
| 5 | beets failed |
| 6 | `restrict` over a key that is restricted already |
| 7 | After `restrict`, the connection still runs other commands |
| 255 | ssh failed |

## Develop

```
uv sync
uv run pytest
```
