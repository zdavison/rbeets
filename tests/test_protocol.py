import pytest

from rbeets.protocol import ProtocolError, decode, encode, error


def test_encode_then_decode_round_trips():
    message = {"type": "progress", "done": 1, "total": 2, "album": "A - B"}
    assert decode(encode(message)) == message


def test_encode_writes_exactly_one_line():
    assert encode({"type": "log", "message": "a\nb"}).count(b"\n") == 1


def test_decode_rejects_plain_text():
    with pytest.raises(ProtocolError):
        decode(b"rbeets-unrestricted\n")


def test_decode_rejects_a_message_without_a_type():
    with pytest.raises(ProtocolError):
        decode(b'{"done": 1}\n')


def test_decode_rejects_an_empty_line():
    with pytest.raises(ProtocolError):
        decode(b"")


def test_error_builds_an_error_event():
    assert error(4, "busy") == {"type": "error", "code": 4, "message": "busy"}
