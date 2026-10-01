"""Both ends, over the real protocol, with tests/fake_ssh.py in place of ssh."""

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RBEETS = shutil.which("rbeets")
SSH = shlex.join([sys.executable, str(Path(__file__).parent / "fake_ssh.py")])
KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJiZWV0cy10ZXN0LWtleS1kYXRhLTAwMDAwMDAw rbeets-test"
OTHER = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDotherkeydata other@laptop"
ALBUM_ID = "11111111-1111-4111-8111-111111111111"


def rbeets(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    assert RBEETS, "run the tests with `uv run pytest`, so that rbeets is on PATH"
    return subprocess.run(
        [RBEETS, "-e", SSH, *args], capture_output=True, env=env or dict(os.environ), timeout=120
    )


def events(done: subprocess.CompletedProcess) -> list[dict]:
    return [json.loads(line) for line in done.stdout.splitlines()]


def test_hello_reports_the_server_versions(root):
    done = rbeets("--json", f"localhost:{root}", "version")
    assert done.returncode == 0, done.stderr
    assert [e["type"] for e in events(done)] == ["ready", "result"]


def test_index_then_stats(root, make_album):
    make_album("Artist A", "First", mb_albumid=ALBUM_ID)
    make_album("Artist B", "Second")
    assert rbeets("--json", f"localhost:{root}", "import", "-A").returncode == 0
    result = events(rbeets("--json", f"localhost:{root}", "stats"))[-1]
    assert (result["albums"], result["tracks"]) == (2, 4)
    assert [m["album"] for m in result["missing_mb_albumid"]] == ["Second"]


def test_refresh_skips_albums_without_an_id_with_no_network(root, make_album):
    make_album("Artist B", "Second")
    rbeets(f"localhost:{root}", "import", "-A")
    result = events(rbeets("--json", f"localhost:{root}", "mbsync"))[-1]
    assert (result["skipped"], result["failed"]) == (1, 0)


def test_human_output_prints_the_result(root):
    done = rbeets(f"localhost:{root}", "version")
    assert done.returncode == 0
    assert b"protocol: 2" in done.stdout


def test_a_missing_root_exits_3(tmp_path):
    assert rbeets(f"localhost:{tmp_path / 'missing'}", "version").returncode == 3


def test_an_ssh_failure_passes_the_ssh_exit_code_through(root):
    failing_ssh = shlex.join([sys.executable, "-c", "import sys; sys.exit(255)"])
    done = subprocess.run(
        [RBEETS, "-e", failing_ssh, f"localhost:{root}", "version"], capture_output=True, timeout=30
    )
    assert done.returncode == 255


@pytest.fixture
def key_setup(tmp_path, isolated_home):
    folder = isolated_home / ".ssh"
    folder.mkdir()
    authorized = folder / "authorized_keys"
    authorized.write_text(f"{OTHER}\n{KEY}\n")
    authorized.chmod(0o600)
    public = tmp_path / "key.pub"
    public.write_text(KEY + "\n")
    return authorized, public


def test_restrict_pins_a_root_with_quotes(tmp_path, key_setup):
    authorized, public = key_setup
    root = tmp_path / """it's "my" music"""
    root.mkdir()
    env = {**os.environ, "FAKE_SSH_KEY": str(public)}

    done = rbeets(f"localhost:{root}", "restrict", str(public), env=env)
    assert done.returncode == 0, done.stderr
    lines = authorized.read_text().splitlines()
    assert lines[0] == OTHER
    assert lines[1].startswith('restrict,command="') and lines[1].endswith(KEY)

    # The pinned key works on its own root, and on no other.
    assert rbeets(f"localhost:{root}", "version", env=env).returncode == 0
    other = tmp_path / "other"
    other.mkdir()
    assert rbeets(f"localhost:{other}", "version", env=env).returncode == 3
    # The pinned key cannot restrict itself again.
    assert rbeets(f"localhost:{root}", "restrict", str(public), env=env).returncode == 6


def test_restrict_reports_a_connection_that_still_runs_other_commands(root, key_setup):
    _, public = key_setup
    # With no FAKE_SSH_KEY, fake_ssh ignores authorized_keys: as ssh does when
    # it connects with a key other than KEY.pub.
    done = rbeets(f"localhost:{root}", "restrict", str(public))
    assert done.returncode == 7
    assert b"-e" in done.stderr


def test_the_server_exits_cleanly_after_the_last_event(root):
    done = rbeets(f"localhost:{root}", "version")
    assert done.returncode == 0
    assert b"Fatal Python error" not in done.stderr
