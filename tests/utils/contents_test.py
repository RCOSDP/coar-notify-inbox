import asyncio
import pytest
from unittest.mock import patch, MagicMock

from db.models import Notification, PushTemplate
from utils.contents import make_contents, make_params


@patch("utils.contents.get_template")
@patch("utils.contents.make_params")
def test_make_contents(mock_make_params, mock_get_template, valid_notification_payload, valid_push_template_payload):
    notification = Notification(**valid_notification_payload)
    template = PushTemplate(**valid_push_template_payload)
    mock_make_params.return_value = {
        "target_uri": notification.target.id,
        "context_uri": notification.context.id,
        "object_uri": notification.object.id,
        "object_name": "Sample Object",
    }
    mock_get_template.return_value = template

    user = MagicMock(language="en")
    title, body, url = asyncio.run(make_contents(notification, user))

    assert title == "Test Title: Sample Object"
    assert body == f"Test Body: {notification.object.id}"
    assert url == notification.context.id
    mock_make_params.assert_called_once_with(notification, user)
    mock_get_template.assert_called_once_with(notification.type, user.language)


@patch("utils.contents.get_template")
@patch("utils.contents.make_params")
def test_make_contents_retry(mock_make_params, mock_get_template, valid_notification_payload, valid_push_template_payload):
    notification = Notification(**valid_notification_payload)
    template = PushTemplate(**valid_push_template_payload)
    mock_make_params.return_value = {
        "target_uri": notification.target.id,
        "context_uri": notification.context.id,
        "object_uri": notification.object.id,
        "object_name": "Sample Object",
    }
    mock_get_template.side_effect = [None, template]

    user = MagicMock(language="ja")
    title, body, url = asyncio.run(make_contents(notification, user))

    assert title == "Test Title: Sample Object"
    assert body == f"Test Body: {notification.object.id}"
    assert url == notification.context.id
    mock_make_params.assert_called_once_with(notification, user)
    mock_get_template.assert_any_call(notification.type, user.language)
    mock_get_template.assert_any_call(notification.type, "en")


@patch("utils.contents.get_template")
@patch("utils.contents.make_params")
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
