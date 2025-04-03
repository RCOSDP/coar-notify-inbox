import pytest
from unittest.mock import AsyncMock, patch
from db.subscriptions import (
    get_push_templates_collection,
    get_subscriptions_collection,
    get_template,
    get_users_collection,
    set_subscription,
    get_subscriptions,
    delete_subscription,
    delete_subscriptions,
    get_user,
    set_template,
    set_user,
)
from db.models import PushTemplate, Subscription, UserProfile


@pytest.mark.asyncio
@patch("db.subscriptions.get_collection")
async def test_get_subscriptions_collection(mock_get_collection):
    mock_get_collection.return_value = AsyncMock()
    collection = await get_subscriptions_collection()
    mock_get_collection.assert_called_once_with("subscriptions")
    assert collection is not None


@pytest.mark.asyncio
@patch("db.subscriptions.get_collection")
async def test_get_users_collection(mock_get_collection):
    mock_get_collection.return_value = AsyncMock()
    collection = await get_users_collection()
    mock_get_collection.assert_called_once_with("userprofiles")
    assert collection is not None


@pytest.mark.asyncio
@patch("db.subscriptions.get_collection")
async def test_get_push_templates_collection(mock_get_collection):
    mock_get_collection.return_value = AsyncMock()
    collection = await get_push_templates_collection()
    mock_get_collection.assert_called_once_with("push_templates")
    assert collection is not None


@pytest.mark.asyncio
@patch("db.subscriptions.get_subscriptions_collection")
async def test_set_subscription(mock_get_subscriptions_collection):
    mock_collection = AsyncMock()
    mock_get_subscriptions_collection.return_value = mock_collection
    subscription = Subscription(endpoint="test_endpoint", target="test_target")
    await set_subscription(subscription)
    mock_collection.update_one.assert_called_once_with(
        {"endpoint": "test_endpoint"},
        {"$set": subscription.model_dump(by_alias=True)},
        upsert=True,
    )


@pytest.mark.asyncio
@patch("db.subscriptions.get_subscriptions_collection")
@pytest.mark.skip(reason="Need to fix the test")
async def test_get_subscriptions(mock_get_subscriptions_collection):
    mock_collection = AsyncMock()
    mock_get_subscriptions_collection.return_value = mock_collection
    mock_collection.find.return_value.to_list.return_value = [
        {"endpoint": "test_endpoint", "target": "test_target"}
    ]
    subscriptions = await get_subscriptions("test_target")
    assert len(subscriptions) == 1
    assert subscriptions[0].endpoint == "test_endpoint"


@pytest.mark.asyncio
@patch("db.subscriptions.get_subscriptions_collection")
async def test_delete_subscription(mock_get_subscriptions_collection):
    mock_collection = AsyncMock()
    mock_get_subscriptions_collection.return_value = mock_collection
    mock_collection.delete_one.return_value.deleted_count = 1
    deleted_count = await delete_subscription("test_endpoint")
    assert deleted_count == 1
    mock_collection.delete_one.assert_called_once_with({"endpoint": "test_endpoint"})


@pytest.mark.asyncio
@patch("db.subscriptions.get_subscriptions_collection")
async def test_delete_subscriptions(mock_get_subscriptions_collection):
    mock_collection = AsyncMock()
    mock_get_subscriptions_collection.return_value = mock_collection
    await delete_subscriptions(["endpoint1", "endpoint2"])
    mock_collection.delete_many.assert_called_once_with({"endpoint": {"$in": ["endpoint1", "endpoint2"]}})


@pytest.mark.asyncio
@patch("db.subscriptions.get_users_collection")
async def test_get_user(mock_get_users_collection):
    mock_collection = AsyncMock()
    mock_get_users_collection.return_value = mock_collection
    mock_collection.find_one.return_value = {"uri": "test_uri", "name": "test_user"}
    user = await get_user("test_uri")
    assert user.uri == "test_uri"


@pytest.mark.asyncio
@patch("db.subscriptions.get_users_collection")
async def test_set_user(mock_get_users_collection):
    mock_collection = AsyncMock()
    mock_get_users_collection.return_value = mock_collection
    user = UserProfile(uri="test_uri", displayname="test_user")
    await set_user(user)
    mock_collection.update_one.assert_called_once_with(
        {"uri": user.uri},
        {"$set": user.model_dump(by_alias=True)},
        upsert=True,
    )

@pytest.mark.asyncio
@patch("db.subscriptions.get_push_templates_collection")
async def test_set_template(mock_get_push_templates_collection, valid_push_template_payload):
    mock_collection = AsyncMock()
    mock_get_push_templates_collection.return_value = mock_collection
    template = PushTemplate(**valid_push_template_payload)
    await set_template(template)
    mock_collection.update_one.assert_called_once_with(
        {"type": template.type, "language": template.language},
        {"$set": template.model_dump(by_alias=True)},
        upsert=True,
    )

@pytest.mark.asyncio
@patch("db.subscriptions.get_push_templates_collection")
async def test_get_template(mock_get_push_templates_collection, valid_push_template_payload):
    mock_collection = AsyncMock()
    mock_get_push_templates_collection.return_value = mock_collection
    mock_collection.find_one.return_value = valid_push_template_payload
    expected_template = PushTemplate(**valid_push_template_payload)
    template = await get_template(expected_template.type, "en")
    assert template == expected_template
    mock_collection.find_one.assert_called_once_with(
        {"type": expected_template.type, "language": "en"},
        {"_id": 0}
    )
