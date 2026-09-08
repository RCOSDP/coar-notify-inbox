from unittest.mock import AsyncMock, patch

import pytest

from db.adapters.base import UpdateResult
from db.models import Notification
from db.notifications import (
    NOTIFICATIONS_COLLECTION_NAME,
    NOTIFICATION_STATES_COLLECTION_NAME,
    FailedToFindNotificationState,
    count_notifications,
    create_notification,
    get_notification,
    get_notification_state_ids_by_status,
    get_notifications,
    delete_notification,
    update_notification_state,
)


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_create_notification(mock_get_adapter, valid_notification_payload):
    adapter = AsyncMock()
    mock_get_adapter.return_value = adapter
    notification_input = Notification(**valid_notification_payload)

    notification_id = await create_notification(notification_input)

    assert adapter.insert_one.call_count == 2
    assert isinstance(notification_id, str)


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_get_notification(mock_get_adapter, notification_id):
    adapter = AsyncMock()
    mock_get_adapter.return_value = adapter

    _ = await get_notification(notification_id)

    adapter.find_one.assert_called_once_with(
        NOTIFICATIONS_COLLECTION_NAME, {"id": notification_id}
    )


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_get_notifications(mock_get_adapter):
    adapter = AsyncMock()
    adapter.find.return_value = []
    mock_get_adapter.return_value = adapter

    notifications = await get_notifications()

    adapter.find.assert_called_once_with(
        NOTIFICATIONS_COLLECTION_NAME, {}, sort=("updated", -1), skip=0, limit=50
    )
    assert notifications == []


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_get_notifications_filters_by_target(mock_get_adapter):
    adapter = AsyncMock()
    adapter.find.return_value = []
    mock_get_adapter.return_value = adapter

    await get_notifications(page=2, page_size=10, target="https://example.org/users/1")

    adapter.find.assert_called_once_with(
        NOTIFICATIONS_COLLECTION_NAME,
        {"target.id": "https://example.org/users/1"},
        sort=("updated", -1),
        skip=10,
        limit=10,
    )


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_delete_notification(mock_get_adapter, notification_id):
    adapter = AsyncMock()
    mock_get_adapter.return_value = adapter

    await delete_notification(notification_id)

    adapter.delete_one.assert_called_once_with(
        NOTIFICATIONS_COLLECTION_NAME, {"id": notification_id}
    )


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_get_notification_state_ids_by_status(mock_get_adapter):
    adapter = AsyncMock()
    adapter.find.return_value = [{"id": "123"}, {"id": "456"}]
    mock_get_adapter.return_value = adapter

    result = await get_notification_state_ids_by_status(read=True)

    adapter.find.assert_called_once_with(
        NOTIFICATION_STATES_COLLECTION_NAME, {"read": True}, limit=50
    )
    assert result == ["123", "456"]


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_update_notification_state_success(mock_get_adapter):
    adapter = AsyncMock()
    adapter.update_one.return_value = UpdateResult(matched=1)
    mock_get_adapter.return_value = adapter

    await update_notification_state(notification_id="123", read=True)

    adapter.update_one.assert_called_once_with(
        NOTIFICATION_STATES_COLLECTION_NAME, {"id": "123"}, {"read": True}
    )


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_update_notification_state_failure(mock_get_adapter):
    adapter = AsyncMock()
    adapter.update_one.return_value = UpdateResult(matched=0)
    mock_get_adapter.return_value = adapter

    with pytest.raises(FailedToFindNotificationState) as exc_info:
        await update_notification_state(notification_id="123", read=True)

    assert "Could not find notification state for notification 123" in str(exc_info.value)


@patch('db.notifications.get_adapter')
@pytest.mark.asyncio
async def test_count_notifications(mock_get_adapter):
    adapter = AsyncMock()
    adapter.count.return_value = 3
    mock_get_adapter.return_value = adapter

    assert await count_notifications() == 3
    adapter.count.assert_called_once_with(NOTIFICATIONS_COLLECTION_NAME, {})
