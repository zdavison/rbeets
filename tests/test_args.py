import pytest

from rbeets.commands import _args, import_
from rbeets.protocol import Failure


def test_parse_splits_flags_and_paths():
    assert _args.parse("import", ["-A", "months"], {"-A"}, 1) == ({"-A"}, ["months"])


def test_an_unknown_flag_is_a_usage_error():
    with pytest.raises(Failure) as caught:
        _args.parse("import", ["-x"], {"-A"}, 1)
    assert caught.value.code == 1


def test_too_many_paths_is_a_usage_error():
    with pytest.raises(Failure) as caught:
        _args.parse("import", ["a", "b"], {"-A"}, 1)
    assert caught.value.code == 1


def test_import_without_a_mode_is_a_usage_error(session):
    with pytest.raises(Failure) as caught:
        import_.run(session, [])
    assert caught.value.code == 1
