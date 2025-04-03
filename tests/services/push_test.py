import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from pywebpush import WebPushException
from services.push import make_contents, make_params, make_payload, send
from db.models import PushTemplate, Subscription
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


@patch("services.push.get_template")
@patch("services.push.make_params")
def test_make_contents(mock_make_params, mock_get_template, valid_notification_payload, valid_push_template_payload):
    notification = Notification(**valid_notification_payload)
    template = PushTemplate(**valid_push_template_payload)
    mock_make_params.return_value = {
        "target_uri": notification.target.id,
        "context_uri": notification.context.id,
        "object_uri": notification.object.id,
    }
    mock_get_template.return_value = template

    user = MagicMock(language="en")
    title, body, url = asyncio.run(make_contents(notification, user))

    assert title == "Test Title"
    assert body == f"Test Body: {notification.object.id}"
    assert url == notification.context.id
    mock_make_params.assert_called_once_with(notification, user)
    mock_get_template.assert_called_once_with(notification.type, user.language)


@patch("services.push.get_template")
@patch("services.push.make_params")
def test_make_contents_retry(mock_make_params, mock_get_template, valid_notification_payload, valid_push_template_payload):
    notification = Notification(**valid_notification_payload)
    template = PushTemplate(**valid_push_template_payload)
    mock_make_params.return_value = {
        "target_uri": notification.target.id,
        "context_uri": notification.context.id,
        "object_uri": notification.object.id,
    }
    mock_get_template.side_effect = [None, template]

    user = MagicMock(language="ja")
    title, body, url = asyncio.run(make_contents(notification, user))

    assert title == "Test Title"
    assert body == f"Test Body: {notification.object.id}"
    assert url == notification.context.id
    mock_make_params.assert_called_once_with(notification, user)
    mock_get_template.assert_any_call(notification.type, user.language)
    mock_get_template.assert_any_call(notification.type, "en")


@patch("services.push.get_template")
@patch("services.push.make_params")
def test_make_contents_no_template(mock_make_params, mock_get_template, valid_notification_payload, valid_push_template_payload):
    notification = Notification(**valid_notification_payload)
    template = PushTemplate(**valid_push_template_payload)
    mock_make_params.return_value = {
        "target_uri": notification.target.id,
        "context_uri": notification.context.id,
        "object_uri": notification.object.id,
    }
    mock_get_template.return_value = None

    user = MagicMock(language="en")
    title, body, url = asyncio.run(make_contents(notification, user))

    assert title == ""
    assert body == ""
    assert url == ""
    mock_make_params.assert_called_with(notification, user)
    mock_get_template.assert_called_with(notification.type, user.language)
    mock_get_template.assert_called_with(notification.type, "en")


def test_make_params(valid_notification_payload):
    notification = Notification(**valid_notification_payload)
    user = MagicMock(language="en", displayname="Test User")
    params = make_params(notification, user)
    assert params["timestamp"] is not None
    assert params["target_uri"] == notification.target.id
    assert params["object_uri"] == notification.object.id
    assert params["context_uri"] == notification.context.id
    assert params["actor_uri"] == notification.actor.id
    assert params["actor_name"] == notification.actor.name
    assert params["target_name"] == "Test User"
