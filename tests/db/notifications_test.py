from unittest.mock import AsyncMock, patch

import pytest

from db.models import Notification
from db.notifications import (
    FailedToFindNotificationState,
    create_notification,
    get_notification,
    get_notification_state_ids_by_status,
    get_notifications,
    delete_notification,
    update_notification_state,
)


@patch('db.notifications.get_collection')
@pytest.mark.asyncio
async def test_create_notification(mock_get_collection, valid_notification_payload):
    mock_get_collection.return_value = AsyncMock()
    notification_input = Notification(**valid_notification_payload)

    notification_id = await create_notification(notification_input)

    assert mock_get_collection.call_count == 2
    assert mock_get_collection.return_value.insert_one.call_count == 2
    assert isinstance(notification_id, str)


@patch('db.notifications.get_collection')
@pytest.mark.asyncio
async def test_get_notification(mock_get_collection, notification_id):
    mock_get_collection.return_value = AsyncMock()

    _ = await get_notification(notification_id)

    mock_get_collection.assert_called_once()
    mock_get_collection.return_value.find_one.assert_called_once()


@patch('db.notifications.get_collection')
@pytest.mark.asyncio
@pytest.mark.skip(reason="Need to rework mocks")
async def test_get_notifications(mock_get_collection):
    mock_collection = AsyncMock()
    mock_collection.find.return_value = AsyncMock()
    mock_get_collection.return_value = mock_collection

    mock_collection.find.return_value.sort.return_value.to_list.return_value = []

    notifications = await get_notifications()

    mock_collection.find.assert_called_once_with({}, {"_id": 0})
    mock_collection.find.return_value.sort.assert_called_once_with("updated", -1)
    mock_collection.find.return_value.sort.return_value.to_list.assert_called_once_with(length=100)
    assert notifications == []


@patch('db.notifications.get_collection')
@pytest.mark.asyncio
async def test_delete_notification(mock_get_collection, notification_id):
    mock_get_collection.return_value = AsyncMock()

    await delete_notification(notification_id)

    mock_get_collection.assert_called_once()
    mock_get_collection.return_value.delete_one.assert_called_once()


@patch('db.notifications.get_collection')
@pytest.mark.asyncio
@pytest.mark.skip(reason="Need to rework mocks")
async def test_get_notification_state_ids_by_status(mock_get_collection):
    mock_collection = AsyncMock()
    mock_get_collection.return_value = mock_collection
    mock_collection.find.return_value.to_list.return_value = [{"id": "123"}, {"id": "456"}]

    result = await get_notification_state_ids_by_status(read=True)

    mock_get_collection.assert_called_once()
    mock_collection.find.assert_called_once_with({"read": True}, {"_id": 0})
    mock_collection.find.return_value.to_list.assert_called_once_with(length=100)
    assert result == ["123", "456"]


@patch('db.notifications.get_collection')
@pytest.mark.asyncio
async def test_update_notification_state_success(mock_get_collection):
    mock_collection = AsyncMock()
    mock_get_collection.return_value = mock_collection
    mock_collection.update_one.return_value.matched_count = 1

    await update_notification_state(notification_id="123", read=True)

    mock_get_collection.assert_called_once()
    mock_collection.update_one.assert_called_once_with({"id": "123"}, {"$set": {"read": True}})


@patch('db.notifications.get_collection')
@pytest.mark.asyncio
async def test_update_notification_state_failure(mock_get_collection):
    mock_collection = AsyncMock()
    mock_get_collection.return_value = mock_collection
    mock_collection.update_one.return_value.matched_count = 0

    with pytest.raises(FailedToFindNotificationState) as exc_info:
        await update_notification_state(notification_id="123", read=True)

    mock_get_collection.assert_called_once()
    mock_collection.update_one.assert_called_once_with({"id": "123"}, {"$set": {"read": True}})
    assert "Could not find notification state for notification 123" in str(exc_info.value)



