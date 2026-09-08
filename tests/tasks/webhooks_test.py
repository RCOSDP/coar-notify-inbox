from unittest.mock import MagicMock, patch

import requests

from db.models import Notification
from tasks.webhooks import send_notification_to_webhook


@patch("tasks.webhooks.requests.post")
def test_send_notification_to_webhook(mock_post, valid_notification_payload):
    mock_post.return_value = MagicMock(status_code=200)
    notification = Notification(**valid_notification_payload)

    send_notification_to_webhook(notification, "https://example.org/hook")

    sent = mock_post.call_args.kwargs["json"]
    assert isinstance(sent, dict)
    assert sent["id"] == notification.id
    assert sent["@context"] == notification.at_context
    assert isinstance(sent["updated"], str)


@patch("tasks.webhooks.requests.post")
def test_send_notification_to_webhook_request_error(mock_post, valid_notification_payload):
    mock_post.side_effect = requests.RequestException("boom")
    notification = Notification(**valid_notification_payload)

    send_notification_to_webhook(notification, "https://example.org/hook")
