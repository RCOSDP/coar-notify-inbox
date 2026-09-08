import asyncio
import binascii
import json
import pytest
from unittest.mock import patch, MagicMock
from pywebpush import WebPushException

from db.models import Notification, Subscription
from services.push import make_payload, send, send_webpush


@pytest.fixture
def mock_subscription():
    subscription = MagicMock(spec=Subscription)
    subscription.model_dump.return_value = {
        "endpoint": "https://example.com",
        "keys": {"p256dh": "key", "auth": "auth"}
    }
    return subscription

@pytest.fixture
def mock_payload():
    return {"title": "Test Notification", "body": "This is a test"}

@patch("services.push.get_settings")
@patch("services.push.webpush")
def test_send_success(mock_webpush, mock_get_settings, mock_subscription, mock_payload):
    mock_get_settings.return_value.vapid_private_key = "private_key"
    mock_get_settings.return_value.vapid_public_key = "public_key"
    mock_get_settings.return_value.subscriber = "mailto:test@example.com"

    send(mock_subscription, mock_payload)

    mock_webpush.assert_called_once_with(
        subscription_info=mock_subscription.model_dump(by_alias=True),
        data=json.dumps(mock_payload),
        vapid_private_key="private_key",
        vapid_claims={"sub": "mailto:test@example.com"}
    )

@patch("services.push.get_settings")
@patch("services.push.webpush")
def test_send_webpush_exception(mock_webpush, mock_get_settings, mock_subscription, mock_payload):
    mock_get_settings.return_value.vapid_private_key = "private_key"
    mock_get_settings.return_value.vapid_public_key = "public_key"
    mock_get_settings.return_value.subscriber = "mailto:test@example.com"

    mock_webpush.side_effect = WebPushException("WebPush error")

    with pytest.raises(WebPushException):
        send(mock_subscription, mock_payload)


@patch("services.push.make_payload")
@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
@patch("services.push.delete_subscriptions")
def test_send_webpush_success(mock_delete_subscriptions, mock_send, mock_get_user, mock_get_subscriptions, mock_make_payload, valid_notification_payload):
    mock_get_subscriptions.return_value = [MagicMock(endpoint="https://example.com")]
    mock_get_user.return_value.displayname = "Test User"
    mock_make_payload.return_value = {"title": "Test Notification"}
    mock_send.return_value = None

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_get_subscriptions.assert_called_once_with(notification.target.id)
    mock_get_user.assert_called_once_with(notification.target.id)
    mock_make_payload.assert_called_once_with(notification, mock_get_user.return_value)
    mock_send.assert_called_once()
    mock_delete_subscriptions.assert_not_called()


@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
def test_send_webpush_no_subscriptions(mock_send, mock_get_user, mock_get_subscriptions, valid_notification_payload):
    mock_get_subscriptions.return_value = []

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_get_subscriptions.assert_called_once_with(notification.target.id)
    mock_get_user.assert_not_called()
    mock_send.assert_not_called()


@patch("services.push.make_payload")
@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
@patch("services.push.delete_subscriptions")
def test_send_webpush_with_invalid_subscription(mock_delete_subscriptions, mock_send, mock_get_user, mock_get_subscriptions, mock_make_payload, valid_notification_payload):
    mock_get_subscriptions.return_value = [MagicMock(endpoint="https://example.com")]
    mock_get_user.return_value.displayname = "Test User"
    mock_make_payload.return_value = {"title": "Test Notification"}
    mock_send.side_effect = WebPushException("test", response=MagicMock(status_code=404))

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_get_subscriptions.assert_called_once_with(notification.target.id)
    mock_get_user.assert_called_once_with(notification.target.id)
    mock_make_payload.assert_called_once_with(notification, mock_get_user.return_value)
    mock_send.assert_called_once()
    mock_delete_subscriptions.assert_called_once_with(["https://example.com"])


@patch("services.push.make_payload")
@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
@patch("services.push.delete_subscriptions")
def test_send_webpush_with_unexpected_error(mock_delete_subscriptions, mock_send, mock_get_user, mock_get_subscriptions, mock_make_payload, valid_notification_payload):
    mock_get_subscriptions.return_value = [MagicMock(endpoint="https://example.com")]
    mock_get_user.return_value.displayname = "Test User"
    mock_make_payload.return_value = {"title": "Test Notification"}
    mock_send.side_effect = WebPushException("test", response=MagicMock(status_code=500))

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_get_subscriptions.assert_called_once_with(notification.target.id)
    mock_get_user.assert_called_once_with(notification.target.id)
    mock_make_payload.assert_called_once_with(notification, mock_get_user.return_value)
    mock_send.assert_called_once()
    mock_delete_subscriptions.assert_not_called()


@patch("services.push.make_contents")
@patch("services.push.get_settings")
def test_make_pyload(mock_get_settings, mock_make_contents, valid_notification_payload):
    mock_get_settings.return_value.icon = "icon_url"
    mock_make_contents.return_value = ("Test Title", "Test Body", "Test URL")

    notification = Notification(**valid_notification_payload)
    user = MagicMock(language="en")

    payload = asyncio.run(make_payload(notification, user))

    assert payload == {
        "title": "Test Title",
        "options": {
            "body": "Test Body",
            "tag": notification.id,
            "icon": "icon_url",
            "badge": "icon_url",
            "requireInteraction": False,
            "data": {
                "url": "Test URL"
            }
        }
    }


@patch("services.push.make_payload")
@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
@patch("services.push.delete_subscriptions")
def test_send_webpush_drops_a_malformed_subscription_and_keeps_going(
    mock_delete_subscriptions, mock_send, mock_get_user, mock_get_subscriptions,
    mock_make_payload, valid_notification_payload
):
    """A subscription whose keys are not valid base64 must not stop the other subscribers.

    pywebpush raises binascii.Error (a ValueError) before making any request, which is not a
    WebPushException, so it used to abort the loop and silently skip everyone after it.
    """
    broken = MagicMock(endpoint="https://example.com/broken")
    healthy = MagicMock(endpoint="https://example.com/healthy")
    mock_get_subscriptions.return_value = [broken, healthy]
    mock_get_user.return_value.displayname = "Test User"
    mock_make_payload.return_value = {"title": "Test Notification"}
    mock_send.side_effect = [binascii.Error("Invalid base64-encoded string"), None]

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    assert mock_send.call_count == 2
    mock_delete_subscriptions.assert_called_once_with(["https://example.com/broken"])


@patch("services.push.make_payload")
@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
@patch("services.push.delete_subscriptions")
def test_send_webpush_keeps_a_subscription_after_a_transient_error(
    mock_delete_subscriptions, mock_send, mock_get_user, mock_get_subscriptions,
    mock_make_payload, valid_notification_payload
):
    """A network failure is not the subscription's fault, so it must survive."""
    mock_get_subscriptions.return_value = [MagicMock(endpoint="https://example.com")]
    mock_get_user.return_value.displayname = "Test User"
    mock_make_payload.return_value = {"title": "Test Notification"}
    mock_send.side_effect = ConnectionError("connection reset")

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_send.assert_called_once()
    mock_delete_subscriptions.assert_not_called()


@patch("services.push.make_payload")
@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
def test_send_webpush_sends_nothing_without_a_template(
    mock_send, mock_get_user, mock_get_subscriptions, mock_make_payload,
    valid_notification_payload
):
    """With no template there is no title, and a blank banner must not be pushed."""
    mock_get_subscriptions.return_value = [MagicMock(endpoint="https://example.com")]
    mock_get_user.return_value.language = "en"
    mock_make_payload.return_value = None

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_send.assert_not_called()


@patch("services.push.make_contents")
@patch("services.push.get_settings")
def test_make_payload_returns_none_without_a_template(
    mock_get_settings, mock_make_contents, valid_notification_payload
):
    mock_get_settings.return_value.icon = "icon_url"
    mock_make_contents.return_value = ("", "", "")

    notification = Notification(**valid_notification_payload)

    assert asyncio.run(make_payload(notification, MagicMock(language="en"))) is None
