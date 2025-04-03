from unittest.mock import patch

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


@patch("routers.subscriptions.delete_subscription")
def test_unsubscribe(mock_delete_subscription, client: TestClient):
    mock_delete_subscription.return_value = 1

    payload = {"endpoint": "https://example.com/endpoint"}

    response = client.post("/unsubscribe", json=payload)

    assert response.status_code == 200
    mock_delete_subscription.assert_called_once_with(payload["endpoint"])


@patch("routers.subscriptions.delete_subscription")
def test_unsubscribe_not_found(mock_delete_subscription, client: TestClient):
    mock_delete_subscription.return_value = 0

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
