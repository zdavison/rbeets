import pytest

from rbeets.target import Target, normalize_root, parse_target


def test_parse_target_splits_host_and_root():
    assert parse_target("user@host:/music") == Target("user@host", "/music")


def test_a_trailing_slash_names_the_same_root():
    assert parse_target("host:/music/").root == "/music"


def test_dot_dot_segments_are_resolved():
    assert normalize_root("/music/../music/./") == "/music"


def test_a_root_keeps_spaces_and_quotes():
    assert parse_target("""host:/it's "my" music""").root == """/it's "my" music"""


def test_a_target_without_a_colon_is_rejected():
    with pytest.raises(ValueError):
        parse_target("host")


def test_a_target_without_a_host_is_rejected():
    with pytest.raises(ValueError):
        parse_target(":/music")


def test_a_relative_root_is_rejected():
    with pytest.raises(ValueError):
        parse_target("host:music")
