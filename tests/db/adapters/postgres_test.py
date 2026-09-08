import json
from datetime import datetime, timezone

from db.adapters.postgres import build_order_by, build_where, decode, encode


def test_encode_wraps_datetimes():
    moment = datetime(2025, 6, 12, 9, 30, tzinfo=timezone.utc)
    encoded = encode({"updated": moment, "nested": {"at": moment}, "items": [moment]})

    assert encoded["updated"] == {"$date": moment.isoformat()}
    assert encoded["nested"]["at"] == {"$date": moment.isoformat()}
    assert encoded["items"] == [{"$date": moment.isoformat()}]


def test_encode_decode_round_trip_keeps_the_type():
    moment = datetime(2025, 6, 12, 9, 30, tzinfo=timezone.utc)
    document = {"id": "urn:uuid:1", "updated": moment, "target": {"id": "u1"}}

    # This is the path a document takes through JSONB.
    restored = decode(json.loads(json.dumps(encode(document))))

    assert restored == document
    assert isinstance(restored["updated"], datetime)


def test_decode_leaves_an_unparsable_date_as_a_string():
    assert decode({"updated": {"$date": "not-a-date"}}) == {"updated": "not-a-date"}


def test_build_where_matches_exactly():
    params = ["notifications"]
    where = build_where({"id": "urn:uuid:1"}, params)

    assert where == "(doc #> $2::text[]) = $3::jsonb"
    assert params[1] == ["id"]
    assert params[2] == json.dumps("urn:uuid:1")


def test_build_where_supports_dotted_keys():
    params = ["notifications"]
    build_where({"target.id": "https://example.org/users/1"}, params)

    assert params[1] == ["target", "id"]


def test_build_where_expands_in():
    params = ["subscriptions"]
    where = build_where({"endpoint": {"$in": ["a", "b"]}}, params)

    assert where == "((doc #> $2::text[]) = $3::jsonb OR (doc #> $4::text[]) = $5::jsonb)"
    assert params[2] == json.dumps("a")
    assert params[4] == json.dumps("b")


def test_build_where_with_an_empty_in_matches_nothing():
    assert build_where({"endpoint": {"$in": []}}, ["subscriptions"]) == "(false)"


def test_build_where_without_a_filter_matches_everything():
    assert build_where({}, ["notifications"]) == "true"


def test_build_where_joins_several_conditions():
    params = ["push_templates"]
    where = build_where({"type": "Announce", "language": "en"}, params)

    assert " AND " in where
    assert len(params) == 5


def test_build_order_by_defaults_to_insertion_order():
    assert build_order_by(None) == " ORDER BY seq ASC"


def test_build_order_by_reaches_inside_the_date_wrapper():
    clause = build_order_by(("updated", -1))

    assert "doc->'updated'->>'$date'" in clause
    assert clause.endswith("DESC")
    assert build_order_by(("updated", 1)).endswith("ASC")


def test_build_order_by_sanitises_the_key():
    assert "'; DROP TABLE" not in build_order_by(("'; DROP TABLE x; --", 1))
