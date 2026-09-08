import json
from datetime import datetime, timezone

from db.adapters.postgres import build_order_by, build_where, decode, encode


def test_encode_wraps_datetimes():
    moment = datetime(2024, 11, 4, 9, 30, tzinfo=timezone.utc)
    encoded = encode({"updated": moment, "nested": {"at": moment}, "items": [moment]})

    assert encoded["updated"] == {"$date": moment.isoformat()}
    assert encoded["nested"]["at"] == {"$date": moment.isoformat()}
    assert encoded["items"] == [{"$date": moment.isoformat()}]


def test_encode_decode_round_trip():
    moment = datetime(2024, 11, 4, 9, 30, tzinfo=timezone.utc)
    document = {"id": "urn:uuid:1", "updated": moment, "target": {"id": "u1"}}

    restored = decode(json.loads(json.dumps(encode(document))))

    assert restored == document
    assert isinstance(restored["updated"], datetime)


def test_decode_invalid_date():
    assert decode({"updated": {"$date": "not-a-date"}}) == {"updated": "not-a-date"}


def test_build_where_exact_match():
    params = ["notifications"]
    where = build_where({"id": "urn:uuid:1"}, params)

    assert where == "(doc #> $2::text[]) = $3::jsonb"
    assert params[1] == ["id"]
    assert params[2] == json.dumps("urn:uuid:1")


def test_build_where_dotted_key():
    params = ["notifications"]
    build_where({"target.id": "https://example.org/users/1"}, params)

    assert params[1] == ["target", "id"]


def test_build_where_in():
    params = ["subscriptions"]
    where = build_where({"endpoint": {"$in": ["a", "b"]}}, params)

    assert where == "((doc #> $2::text[]) = $3::jsonb OR (doc #> $4::text[]) = $5::jsonb)"
    assert params[2] == json.dumps("a")
    assert params[4] == json.dumps("b")


def test_build_where_empty_in():
    assert build_where({"endpoint": {"$in": []}}, ["subscriptions"]) == "(false)"


def test_build_where_no_filter():
    assert build_where({}, ["notifications"]) == "true"


def test_build_where_multiple_conditions():
    params = ["push_templates"]
    where = build_where({"type": "Announce", "language": "en"}, params)

    assert " AND " in where
    assert len(params) == 5


def test_build_order_by_default():
    assert build_order_by(None) == " ORDER BY seq ASC"


def test_build_order_by_direction():
    clause = build_order_by(("updated", -1))

    assert "doc->'updated'->>'$date'" in clause
    assert clause.endswith("DESC")
    assert build_order_by(("updated", 1)).endswith("ASC")


def test_build_order_by_sanitises_key():
    assert "'; DROP TABLE" not in build_order_by(("'; DROP TABLE x; --", 1))
