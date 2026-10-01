import pytest

from rbeets.commands import restrict
from rbeets.protocol import Failure

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJiZWV0cy10ZXN0LWtleS1kYXRhLTAwMDAwMDAw"


@pytest.fixture
def authorized(isolated_home):
    folder = isolated_home / ".ssh"
    folder.mkdir()
    path = folder / "authorized_keys"
    path.write_text(KEY + " rbeets\n")
    return path


def test_restrict_pins_the_key_to_this_root(session, authorized):
    session.executable = "/opt/rbeets/bin/rbeets"
    result = restrict.run(session, [KEY])
    expected = f"/opt/rbeets/bin/rbeets --server --root {session.root} --pinned"
    assert result == {"forced_command": expected}
    assert authorized.read_text() == f'restrict,command="{expected}" {KEY} rbeets\n'


def test_restrict_over_a_restricted_key_is_not_allowed(session, authorized):
    session.pinned = True
    with pytest.raises(Failure) as caught:
        restrict.run(session, [KEY])
    assert caught.value.code == 6
    assert authorized.read_text() == KEY + " rbeets\n"


def test_restrict_without_authorized_keys_fails_with_code_3(session):
    with pytest.raises(Failure) as caught:
        restrict.run(session, [KEY])
    assert caught.value.code == 3


def test_restrict_with_a_bad_key_is_a_usage_error(session, authorized):
    with pytest.raises(Failure) as caught:
        restrict.run(session, ["not a key"])
    assert caught.value.code == 1
