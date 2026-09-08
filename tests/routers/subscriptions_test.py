from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from db.models import PushTemplate
from routers.subscriptions import SubscribeRequest, UnsubscribeRequest, UserProfileRequest


@patch("routers.subscriptions.get_settings")
def test_get_vapid_public_key(mock_get_settings, client: TestClient):
    mock_get_settings.return_value.vapid_public_key = "test_public_key"

    response = client.get("/inbox/subscription/vapid-public-key")

    assert response.status_code == 200
    assert response.text == "test_public_key"


@patch("routers.subscriptions.set_subscription")
def test_subscribe(mock_set_subscription, client: TestClient, valid_subscribe_payload: dict):
    mock_set_subscription.return_value = 1

    response = client.post("/subscribe", json=valid_subscribe_payload)

    assert response.status_code == 201
    mock_set_subscription.assert_called_once_with(SubscribeRequest(**valid_subscribe_payload))


@patch("routers.subscriptions.set_subscription")
def test_subscribe_already_exists(mock_set_subscription, client: TestClient, valid_subscribe_payload: dict):
    mock_set_subscription.return_value = 0

    response = client.post("/subscribe", json=valid_subscribe_payload)

    assert response.status_code == 200
    mock_set_subscription.assert_called_once_with(SubscribeRequest(**valid_subscribe_payload))


@patch("routers.subscriptions.get_subscription")
@patch("routers.subscriptions.delete_subscription")
def test_unsubscribe(mock_delete_subscription, mock_get_subscription, client: TestClient):
    mock_delete_subscription.return_value = 1
    mock_get_subscription.return_value = None

    payload = {"endpoint": "https://example.com/endpoint"}

    response = client.post("/unsubscribe", json=payload)

    assert response.status_code == 200
    mock_delete_subscription.assert_called_once_with(payload["endpoint"])


@patch("routers.subscriptions.get_subscription")
@patch("routers.subscriptions.delete_subscription")
def test_unsubscribe_not_found(
    mock_delete_subscription, mock_get_subscription, client: TestClient
):
    mock_delete_subscription.return_value = 0
    mock_get_subscription.return_value = None

    payload = {"endpoint": "https://example.com/endpoint"}

    response = client.post("/unsubscribe", json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Subscription not found"}
    mock_delete_subscription.assert_called_once_with(payload["endpoint"])


@patch("routers.subscriptions.set_user")
def test_user_profile(mock_set_user, client: TestClient, valid_userprofile_payload: dict):
    mock_set_user.return_value = True

    response = client.post("/userprofile", json=valid_userprofile_payload)

    assert response.status_code == 201
    mock_set_user.assert_called_once_with(UserProfileRequest(**valid_userprofile_payload))


@patch("routers.subscriptions.set_user")
def test_user_profile_already_exists(mock_set_user, client: TestClient, valid_userprofile_payload: dict):
    mock_set_user.return_value = False

    response = client.post("/userprofile", json=valid_userprofile_payload)

    assert response.status_code == 200
    mock_set_user.assert_called_once_with(UserProfileRequest(**valid_userprofile_payload))


@patch("routers.subscriptions.set_template")
def test_update_push_template(mock_set_template, admin_client: TestClient, valid_push_template_payload: dict):
    mock_set_template.return_value = True

    response = admin_client.post("/push-template", json=valid_push_template_payload)

    assert response.status_code == 201
    mock_set_template.assert_called_once_with(PushTemplate(**valid_push_template_payload))


@patch("routers.subscriptions.set_template")
def test_update_push_template_already_exists(mock_set_template, admin_client: TestClient, valid_push_template_payload: dict):
    mock_set_template.return_value = False

    response = admin_client.post("/push-template", json=valid_push_template_payload)

    assert response.status_code == 200
    mock_set_template.assert_called_once_with(PushTemplate(**valid_push_template_payload))


@patch("routers.subscriptions.set_subscription")
@patch("routers.subscriptions.authorise")
def test_subscribe_authorises_the_target(mock_authorise, mock_set_subscription, client):
    mock_set_subscription.return_value = True

    client.post(
        "/subscribe",
        json={"target": "https://example.org/users/1", "endpoint": "https://push/1"},
    )

    assert mock_authorise.call_args.args[1] == "https://example.org/users/1"


@patch("routers.subscriptions.delete_subscription")
@patch("routers.subscriptions.get_subscription")
@patch("routers.subscriptions.authorise")
def test_unsubscribe_authorises_against_the_stored_target(
    mock_authorise, mock_get_subscription, mock_delete_subscription, client
):
    """The request carries only an endpoint, so the target has to come from storage."""
    mock_get_subscription.return_value = MagicMock(target="https://example.org/users/1")
    mock_delete_subscription.return_value = 1

    client.post("/unsubscribe", json={"endpoint": "https://push/1"})

    assert mock_authorise.call_args.args[1] == "https://example.org/users/1"


@patch("routers.subscriptions.set_user")
@patch("routers.subscriptions.authorise")
def test_userprofile_authorises_the_uri(mock_authorise, mock_set_user, client):
    mock_set_user.return_value = True

    client.post("/userprofile", json={"uri": "https://example.org/users/1"})

    assert mock_authorise.call_args.args[1] == "https://example.org/users/1"
