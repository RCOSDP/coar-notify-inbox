from datetime import datetime

from db.models import Notification

# pytest tests/db/models_test.py

# pytest tests/db/models_test.py::test_notification
def test_notification(valid_notification_payload):
    notification = Notification(**valid_notification_payload)
    assert notification.id

# pytest tests/db/models_test.py::test_notification_provides_default_updated_value
def test_notification_provides_default_updated_value(valid_notification_payload):
    notification = Notification(**valid_notification_payload)
    assert notification.updated

# pytest tests/db/models_test.py::test_notification_validate_updated_value
def test_notification_validate_updated_value(valid_notification_payload):
    valid_notification_payload["updated"] = "2021-01-01T00:00:00Z"
    notification = Notification(**valid_notification_payload)
    assert notification.updated == datetime.fromisoformat("2021-01-01T00:00:00Z")

    valid_notification_payload["updated"] = "2021-01-01T00:00:00+09:00"
    notification = Notification(**valid_notification_payload)
    assert notification.updated == datetime.fromisoformat("2021-01-01T00:00:00+09:00")

    valid_notification_payload["updated"] = "2021-01-01T00:00:00+0900"
    notification = Notification(**valid_notification_payload)
    assert notification.updated == datetime.fromisoformat("2021-01-01T00:00:00+09:00")


def test_notification_handles_at_context_alias(valid_notification_payload):
    notification = Notification(**valid_notification_payload)
    assert notification.at_context == valid_notification_payload["@context"]


def test_notification_handles_ietf_cite_as_alias(valid_notification_payload):
    notification = Notification(**valid_notification_payload)
    assert (notification.object.ietf_cite_as ==
            valid_notification_payload["object"]["ietf:cite-as"])


def test_notification_handles_valid_offer_review_payload(valid_offer_review_payload):
    notification = Notification(**valid_offer_review_payload)
    assert notification.id
