import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from pywebpush import WebPushException
from services.push import send
from db.models import Subscription
from services.push import send_webpush
from db.models import Notification



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


@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
@patch("services.push.delete_subscriptions")
def test_send_webpush_success(mock_delete_subscriptions, mock_send, mock_get_user, mock_get_subscriptions, valid_notification_payload):
    mock_get_subscriptions.return_value = [MagicMock(endpoint="https://example.com")]
    mock_get_user.return_value.displayname = "Test User"
    mock_send.return_value = None

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_get_subscriptions.assert_called_once_with(notification.target.id)
    mock_get_user.assert_called_once_with(notification.target.id)
    mock_send.assert_called_once()
    mock_delete_subscriptions.assert_called_once_with([])

@patch("services.push.get_subscriptions")
@patch("services.push.get_user")
@patch("services.push.send")
@patch("services.push.delete_subscriptions")
def test_send_webpush_with_invalid_subscription(mock_delete_subscriptions, mock_send, mock_get_user, mock_get_subscriptions, valid_notification_payload):
    mock_get_subscriptions.return_value = [MagicMock(endpoint="https://example.com")]
    mock_get_user.return_value.displayname = "Test User"
    mock_send.side_effect = WebPushException("test", response=MagicMock(status_code=404))

    notification = Notification(**valid_notification_payload)

    asyncio.run(send_webpush(notification))

    mock_get_subscriptions.assert_called_once_with(notification.target.id)
    mock_get_user.assert_called_once_with(notification.target.id)
    mock_send.assert_called_once()
    mock_delete_subscriptions.assert_called_once_with(["https://example.com"])
