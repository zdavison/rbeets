import shlex
import stat

import pytest

from rbeets.authkeys import (
    PublicKey,
    forced_command_for,
    install,
    parse_public_key,
    rewrite,
    split_line,
)
from rbeets.protocol import Failure

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJiZWV0cy10ZXN0LWtleS1kYXRhLTAwMDAwMDAw"
OTHER = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQDotherkeydata other@laptop"
FORCED = "/home/u/.local/bin/rbeets --server --root /music --pinned"


def test_parse_public_key_reads_a_pub_file():
    assert parse_public_key(KEY + " music@library-host\n") == PublicKey(
        "ssh-ed25519", KEY.split()[1]
    )


def test_parse_public_key_rejects_text_that_is_not_a_key():
    with pytest.raises(ValueError):
        parse_public_key("hello world")


def test_split_line_reads_options_with_quoted_spaces():
    line = 'command="echo a, b",no-pty ' + KEY + " comment here"
    options, key, comment = split_line(line)
    assert options == 'command="echo a, b",no-pty'
    assert key.type == "ssh-ed25519"
    assert comment == "comment here"


def test_split_line_skips_comments_and_blank_lines():
    assert split_line("# a comment") is None
    assert split_line("   ") is None


def test_rewrite_restricts_the_matching_line_only():
    content = f"{OTHER}\n{KEY} rbeets\n".encode()
    lines = rewrite(content, parse_public_key(KEY), FORCED).decode().splitlines()
    assert lines[0] == OTHER
    assert lines[1] == f'restrict,command="{FORCED}" {KEY} rbeets'


def test_rewrite_replaces_existing_options():
    content = f"no-pty,from=\"10.0.0.1\" {KEY}\n".encode()
    line = rewrite(content, parse_public_key(KEY), FORCED).decode()
    assert line == f'restrict,command="{FORCED}" {KEY}\n'


def test_rewrite_keeps_other_lines_byte_for_byte():
    content = b"# keys\r\n" + OTHER.encode() + b"  \r\n" + KEY.encode()
    result = rewrite(content, parse_public_key(KEY), FORCED)
    assert result.startswith(b"# keys\r\n" + OTHER.encode() + b"  \r\n")
    assert not result.endswith(b"\n")


def test_rewrite_without_a_matching_line_fails_with_code_3():
    with pytest.raises(Failure) as caught:
        rewrite(OTHER.encode() + b"\n", parse_public_key(KEY), FORCED)
    assert caught.value.code == 3


def test_rewrite_with_two_matching_lines_fails_with_code_3():
    with pytest.raises(Failure) as caught:
        rewrite(f"{KEY}\n{KEY}\n".encode(), parse_public_key(KEY), FORCED)
    assert caught.value.code == 3


def test_forced_command_round_trips_a_root_with_quotes():
    forced = shlex.join(["/bin/rbeets", "--server", "--root", """/it's "my" music""", "--pinned"])
    content = rewrite(f"{KEY}\n".encode(), parse_public_key(KEY), forced)
    assert forced_command_for(content, parse_public_key(KEY)) == forced


def test_forced_command_for_an_unrestricted_key_is_none():
    assert forced_command_for(f"{KEY}\n".encode(), parse_public_key(KEY)) is None


def test_install_replaces_the_file_with_mode_600(tmp_path):
    folder = tmp_path / "ssh"
    folder.mkdir()
    path = folder / "authorized_keys"
    path.write_text("old\n")
    path.chmod(0o644)
    install(path, b"new\n")
    assert path.read_bytes() == b"new\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in folder.iterdir()] == ["authorized_keys"]
