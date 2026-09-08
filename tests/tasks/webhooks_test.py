from unittest.mock import MagicMock, patch

from db.models import Notification
from tasks.webhooks import send_notification_to_webhook


@patch("tasks.webhooks.requests.post")
def test_send_notification_to_webhook_posts_the_notification_itself(
    mock_post, valid_notification_payload
):
    """The webhook must receive the notification as a JSON object.

    json= takes the object to serialise. Passing a string produced a JSON-encoded string, and
    json.dumps(default=str) on a Pydantic model stringified it with repr(), so the receiver got
    valid JSON that was not the notification.
    """
    mock_post.return_value = MagicMock(status_code=200)
    notification = Notification(**valid_notification_payload)

    send_notification_to_webhook(notification, "https://example.org/hook")

    sent = mock_post.call_args.kwargs["json"]
    assert isinstance(sent, dict)
    assert sent["id"] == notification.id
    assert sent["@context"] == notification.at_context
    # mode="json" means the datetime is rendered, so the body is serialisable as-is.
    assert isinstance(sent["updated"], str)


@patch("tasks.webhooks.requests.post")
def test_send_notification_to_webhook_swallows_request_errors(
    mock_post, valid_notification_payload
):
    import requests

    mock_post.side_effect = requests.RequestException("boom")
    notification = Notification(**valid_notification_payload)

    # A failing webhook must not propagate into the request that triggered it.
    send_notification_to_webhook(notification, "https://example.org/hook")
