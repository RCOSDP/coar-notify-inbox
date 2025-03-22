import pytest
from datetime import datetime, timedelta, timezone
from utils import InboxDatetime, datetime_to_inboxdatetime


def test_inboxdatetime_rfc3339format():
    dt = InboxDatetime.fromisoformat("2022-10-06T15:00:00+00:00")
    assert dt.rfc3339format() == "2022-10-06T15:00:00Z"

    dt = InboxDatetime.fromisoformat("2022-10-07T00:00:00+09:00")
    assert dt.rfc3339format() == "2022-10-07T00:00:00+09:00"


def test_datetime_to_inboxdatetime():
    dt = datetime.now(timezone.utc)
    idt = datetime_to_inboxdatetime(dt)
    assert idt == InboxDatetime.fromisoformat(dt.isoformat())
