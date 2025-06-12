from datetime import datetime


class InboxDatetime(datetime):

    def rfc3339format(self):
        """Return the current time in RFC3339 format.

        Example:
        >>> InboxDatetime.now(timezone.utc).rfc3339format()
        "2025-03-05T14:00:00Z"
        >>> InboxDatetime.now(ZoneInfo("Asia/Tokyo")).rfc3339format()
        "2025-03-05T23:00:00+09:00"
        """
        return self.isoformat(timespec="seconds").replace("+00:00", "Z")


def datetime_to_inboxdatetime(dt: datetime):
    return InboxDatetime.fromisoformat(dt.isoformat())
