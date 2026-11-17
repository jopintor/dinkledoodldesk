from app.utils import (
    decode_cursor,
    encode_cursor,
    parse_ticket_ref,
    slugify,
    ticket_number,
)


def test_ticket_number_counts_up_with_padding():
    assert ticket_number(1) == "DD-000001"
    assert ticket_number(42) == "DD-000042"


def test_parse_ticket_ref_accepts_number_or_id():
    assert parse_ticket_ref("DD-000042") == 42
    assert parse_ticket_ref("42") == 42
    assert parse_ticket_ref("abc") is None


def test_cursor_roundtrip():
    assert decode_cursor(encode_cursor(99)) == 99
    assert decode_cursor("not-a-cursor") is None


def test_slugify():
    assert slugify("Court booking") == "court-booking"
