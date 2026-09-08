from unittest.mock import AsyncMock, patch

import pytest

from db.adapters.base import UpdateResult
from db.models import PushTemplate, Subscription, UserProfile
from db.subscriptions import (
    normalise_type,
    PUSH_TEMPLATES_COLLECTION_NAME,
    SUBSCRIPTIONS_COLLECTION_NAME,
    USERS_COLLECTION_NAME,
    delete_subscription,
    delete_subscriptions,
    get_subscriptions,
    get_template,
    get_user,
    set_subscription,
    set_template,
    set_user,
)


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_set_subscription_creates(mock_get_adapter):
    adapter = AsyncMock()
    adapter.update_one.return_value = UpdateResult(matched=0, inserted=True)
    mock_get_adapter.return_value = adapter
    subscription = Subscription(endpoint="test_endpoint", target="test_target")

    assert await set_subscription(subscription) is True
    adapter.update_one.assert_called_once_with(
        SUBSCRIPTIONS_COLLECTION_NAME,
        {"endpoint": "test_endpoint"},
        subscription.model_dump(by_alias=True),
        upsert=True,
    )


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_set_subscription_updates(mock_get_adapter):
    adapter = AsyncMock()
    adapter.update_one.return_value = UpdateResult(matched=1, inserted=False)
    mock_get_adapter.return_value = adapter

    result = await set_subscription(
        Subscription(endpoint="test_endpoint", target="test_target")
    )

    assert result is False


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_get_subscriptions(mock_get_adapter):
    adapter = AsyncMock()
    adapter.find.return_value = [
        {"endpoint": "test_endpoint", "target": "test_target"}
    ]
    mock_get_adapter.return_value = adapter

    subscriptions = await get_subscriptions("test_target")

    adapter.find.assert_called_once_with(
        SUBSCRIPTIONS_COLLECTION_NAME, {"target": "test_target"}, limit=100
    )
    assert len(subscriptions) == 1
    assert subscriptions[0].endpoint == "test_endpoint"


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_delete_subscription(mock_get_adapter):
    adapter = AsyncMock()
    adapter.delete_one.return_value = 1
    mock_get_adapter.return_value = adapter

    assert await delete_subscription("test_endpoint") == 1
    adapter.delete_one.assert_called_once_with(
        SUBSCRIPTIONS_COLLECTION_NAME, {"endpoint": "test_endpoint"}
    )


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_delete_subscriptions(mock_get_adapter):
    adapter = AsyncMock()
    mock_get_adapter.return_value = adapter

    await delete_subscriptions(["endpoint1", "endpoint2"])

    adapter.delete_many.assert_called_once_with(
        SUBSCRIPTIONS_COLLECTION_NAME,
        {"endpoint": {"$in": ["endpoint1", "endpoint2"]}},
    )


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_get_user(mock_get_adapter):
    adapter = AsyncMock()
    adapter.find_one.return_value = {"uri": "test_uri", "name": "test_user"}
    mock_get_adapter.return_value = adapter

    user = await get_user("test_uri")

    adapter.find_one.assert_called_once_with(USERS_COLLECTION_NAME, {"uri": "test_uri"})
    assert user.uri == "test_uri"


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_get_user_missing(mock_get_adapter):
    adapter = AsyncMock()
    adapter.find_one.return_value = None
    mock_get_adapter.return_value = adapter

    assert await get_user("test_uri") is None


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_set_user(mock_get_adapter):
    adapter = AsyncMock()
    adapter.update_one.return_value = UpdateResult(matched=0, inserted=True)
    mock_get_adapter.return_value = adapter
    user = UserProfile(uri="test_uri", displayname="test_user")

    assert await set_user(user) is True
    adapter.update_one.assert_called_once_with(
        USERS_COLLECTION_NAME,
        {"uri": user.uri},
        user.model_dump(by_alias=True),
        upsert=True,
    )


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_set_template(mock_get_adapter, valid_push_template_payload):
    adapter = AsyncMock()
    adapter.update_one.return_value = UpdateResult(matched=0, inserted=True)
    mock_get_adapter.return_value = adapter
    template = PushTemplate(**valid_push_template_payload)

    assert await set_template(template) is True
    adapter.update_one.assert_called_once_with(
        PUSH_TEMPLATES_COLLECTION_NAME,
        {"type": template.type, "language": template.language},
        template.model_dump(by_alias=True),
        upsert=True,
    )


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_get_template(mock_get_adapter, valid_push_template_payload):
    adapter = AsyncMock()
    adapter.find_one.return_value = valid_push_template_payload
    mock_get_adapter.return_value = adapter
    expected_template = PushTemplate(**valid_push_template_payload)

    template = await get_template(expected_template.type, "en")

    adapter.find_one.assert_called_once_with(
        PUSH_TEMPLATES_COLLECTION_NAME,
        {"type": expected_template.type, "language": "en"},
    )
    assert template == expected_template


def test_normalise_type_sorts_a_list():
    assert normalise_type(["coar-notify:IngestAction", "Announce"]) == [
        "Announce", "coar-notify:IngestAction"
    ]


def test_normalise_type_leaves_a_string_alone():
    assert normalise_type("Announce") == "Announce"


@pytest.mark.asyncio
@patch("db.subscriptions.get_adapter")
async def test_get_template_matches_regardless_of_type_order(mock_get_adapter):
    """The COAR Notify type is a set, so the lookup must not depend on the order it arrives in."""
    adapter = AsyncMock()
    adapter.find_one.return_value = None
    mock_get_adapter.return_value = adapter

    await get_template(["coar-notify:IngestAction", "Announce"], "en")

    adapter.find_one.assert_called_once_with(
        PUSH_TEMPLATES_COLLECTION_NAME,
        {"type": ["Announce", "coar-notify:IngestAction"], "language": "en"},
    )
