import io
import os
import subprocess
import sys
import threading

from rbeets.commands import COMMANDS
from rbeets.protocol import PROTOCOL, decode, encode
from rbeets.server import serve, watch
from rbeets.state import lock, state_dir


def hello(root, command="hello", args=(), protocol=PROTOCOL) -> dict:
    return {
        "type": "hello",
        "protocol": protocol,
        "rbeets": "test",
        "command": command,
        "args": list(args),
        "root": str(root),
    }


def exchange(root, first_line: bytes, pinned=False) -> tuple[int, list[dict]]:
    """Run serve() with FIRST_LINE as the client's input. The input stays open
    until serve() returns, as a real client's does."""
    read_end, write_end = os.pipe()
    os.write(write_end, first_line)
    out = io.BytesIO()
    with os.fdopen(read_end, "rb") as inp:
        code = serve(str(root), pinned, inp, out)
        os.close(write_end)
    return code, [decode(line) for line in out.getvalue().splitlines()]


def test_hello_answers_ready_then_result(root):
    code, events = exchange(root, encode(hello(root)))
    assert code == 0
    assert [e["type"] for e in events] == ["ready", "result"]
    assert events[1]["protocol"] == PROTOCOL
    assert events[1]["root"] == str(root)


def test_another_protocol_version_exits_2_with_the_upgrade_command(root):
    code, events = exchange(root, encode(hello(root, protocol=PROTOCOL + 1)))
    assert code == 2
    assert [e["type"] for e in events] == ["error"]
    assert "pipx upgrade rbeets" in events[0]["message"]


def test_text_instead_of_hello_exits_2(root):
    assert exchange(root, b"hi\n")[0] == 2


def test_a_root_other_than_the_servers_exits_3(root, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    code, events = exchange(root, encode(hello(other)))
    assert code == 3
    assert str(root) in events[0]["message"]


def test_a_missing_root_exits_3(tmp_path):
    missing = tmp_path / "missing"
    assert exchange(missing, encode(hello(missing)))[0] == 3


def test_a_trailing_slash_names_the_same_root(root):
    assert exchange(root, encode(hello(f"{root}/")))[0] == 0


def test_an_unknown_command_exits_1(root):
    assert exchange(root, encode(hello(root, command="rm")))[0] == 1


def test_restrict_on_a_pinned_server_exits_6(root):
    assert exchange(root, encode(hello(root, "restrict", ["k"])), pinned=True)[0] == 6


def test_a_second_command_on_a_locked_root_is_busy(root, make_album):
    make_album("Artist A", "First")
    with lock(state_dir(str(root))):
        code, events = exchange(root, encode(hello(root, "index")))
    assert code == 4
    assert [e["type"] for e in events] == ["ready", "error"]
    assert not (state_dir(str(root)) / "library.db").exists()


def test_a_beets_exception_exits_5(root, monkeypatch):
    def broken(session, args):
        raise RuntimeError("database is locked")

    monkeypatch.setitem(COMMANDS, "stats", broken)
    code, events = exchange(root, encode(hello(root, "stats")))
    assert code == 5
    assert "RuntimeError: database is locked" in events[-1]["message"]


def test_watch_sets_stopped_at_end_of_input():
    stopped = threading.Event()
    watch(io.BytesIO(b""), stopped)
    assert stopped.is_set()


def test_protect_stdout_moves_prints_to_stderr():
    program = (
        "from rbeets.server import protect_stdout\n"
        "out = protect_stdout()\n"
        "print('beets noise')\n"
        "out.write(b'protocol\\n')\n"
    )
    done = subprocess.run([sys.executable, "-c", program], capture_output=True, check=True)
    assert done.stdout == b"protocol\n"
    assert b"beets noise" in done.stderr
