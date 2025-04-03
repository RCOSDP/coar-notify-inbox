from unittest.mock import patch

import pytest

from fastapi.testclient import TestClient


def test_read_inbox_options(client: TestClient):
    response = client.options("/inbox/")

    assert response.status_code == 200
    assert response.headers["Accept-Post"] == "application/ld+json"


@patch("routers.inbox.get_notifications")
def test_read_inbox(mock_get_notifications, client: TestClient):
    mock_get_notifications.return_value = []

    response = client.get("/inbox/")

    assert response.status_code == 200
    assert response.json() == {
        "@context": "http://www.w3.org/ns/ldp",
        "@id": "http://testserver/inbox",
        "contains": [],
    }


@patch("routers.inbox.send_webpush")
@patch("routers.inbox.get_notification")
@patch("routers.inbox.create_notification")
def test_add_notification(
    mock_create_notification, mock_get_notification, mock_send_webpush,
    valid_notification_payload: dict, client: TestClient
):
    mock_get_notification.return_value = None
    mock_create_notification.return_value = valid_notification_payload["id"]

    response = client.post("/inbox/", json=valid_notification_payload)

    assert response.status_code == 201
    assert (response.headers["Location"] ==
            f"http://testserver/inbox/{valid_notification_payload['id']}")


@patch("routers.inbox.get_notification")
def test_add_notification_conflict(
    mock_get_notification, valid_notification_payload: dict, client: TestClient
):
    mock_get_notification.return_value = valid_notification_payload

    response = client.post("/inbox/", json=valid_notification_payload)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "ID conflict: notification with this ID already exists."
    }

@patch("routers.inbox.send_webpush")
@patch("routers.inbox.get_settings")
@patch("routers.inbox.get_notification")
@patch("routers.inbox.create_notification")
def test_add_notification_no_push(
    mock_create_notification, mock_get_notification, mock_get_settings, mock_send_webpush,
    valid_notification_payload: dict, client: TestClient
):
    mock_get_notification.return_value = None
    mock_create_notification.return_value = valid_notification_payload["id"]
    mock_get_settings.return_value.enable_push_notifications = False

    response = client.post("/inbox/", json=valid_notification_payload)

    assert response.status_code == 201
    assert not mock_send_webpush.called


@patch("routers.inbox.get_notification")
def test_read_notification(mock_get_notification,
                           valid_notification_payload: dict,
                           client: TestClient):
    mock_notification = {
        "updated": "2022-10-06T15:00:00.000000",
        **valid_notification_payload
    }

    mock_get_notification.return_value = mock_notification

    response = client.get(f"/inbox/{valid_notification_payload['id']}/")

    assert response.status_code == 200
    assert response.json() == mock_notification


@pytest.mark.skip(reason="Skipping until coar_notify_validator is fixed")
@patch("routers.inbox.create_notification")
def test_add_notification_validation_failure(mock_create_notification,
                                             invalid_notification_payload: dict,
                                             client: TestClient):
    mock_create_notification.return_value = invalid_notification_payload["id"]

    response = client.post("/inbox/", json=invalid_notification_payload)

    assert response.status_code == 400
    assert response.json() == {
        "detail": [
            {
                "focus_node": "<https://bioxriv.org/",
                "message": "Less than 1 values on <https://bioxriv.org/-ldp:inbox",
                "result_path": "ldp:inbox",
                "severity": "sh:Violation",
                "source_shape": "ex:InboxShape"
            }
        ]
    }


@patch("routers.inbox.get_notification")
def test_read_notification_not_found(
    mock_get_notification, valid_notification_payload: dict, client: TestClient
):
    mock_get_notification.return_value = None

    response = client.get(f"/inbox/{valid_notification_payload['id']}/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Notification not found."}
