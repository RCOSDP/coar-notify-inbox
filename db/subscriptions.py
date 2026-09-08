from db import get_adapter
from db.models import Subscription, UserProfile, PushTemplate
from utils import logger


SUBSCRIPTIONS_COLLECTION_NAME = "subscriptions"
USERS_COLLECTION_NAME = "userprofiles"
PUSH_TEMPLATES_COLLECTION_NAME = "push_templates"


def normalise_type(activity_type):
    """Return a canonical form of a notification type for template lookups.

    A COAR Notify type is a set - ["Announce", "coar-notify:IngestAction"] means the same as the
    other order - but it arrives as a list and was matched for equality, so a sender listing the
    values in a different order found no template at all. Sorting on both write and read makes the
    match order-independent.
    """
    if isinstance(activity_type, str):
        return activity_type
    return sorted(activity_type)


async def set_subscription(subscription: Subscription):
    """Store a subscription, returning True when it was newly created.

    routers/subscriptions.py answers 201 on a create and 200 on an update, so the return
    value has to distinguish the two.
    """
    adapter = await get_adapter()
    result = await adapter.update_one(
        SUBSCRIPTIONS_COLLECTION_NAME,
        {"endpoint": subscription.endpoint},
        subscription.model_dump(by_alias=True),
        upsert=True,
    )
    return result.inserted


async def get_subscriptions(target: str):
    adapter = await get_adapter()
    subscriptions = await adapter.find(
        SUBSCRIPTIONS_COLLECTION_NAME, {"target": target}, limit=100
    )
    return [Subscription(**subscription) for subscription in subscriptions]


async def get_subscription(endpoint: str):
    """Look up a single subscription, so a caller can be checked against its target."""
    adapter = await get_adapter()
    subscription = await adapter.find_one(
        SUBSCRIPTIONS_COLLECTION_NAME, {"endpoint": endpoint}
    )
    return Subscription(**subscription) if subscription is not None else None


async def delete_subscription(endpoint: str) -> int:
    adapter = await get_adapter()
    return await adapter.delete_one(SUBSCRIPTIONS_COLLECTION_NAME, {"endpoint": endpoint})


async def delete_subscriptions(endpoints: list[str]):
    adapter = await get_adapter()
    await adapter.delete_many(
        SUBSCRIPTIONS_COLLECTION_NAME, {"endpoint": {"$in": endpoints}}
    )
    logger.info(f"Deleted {len(endpoints)} subscriptions")


async def get_user(uri: str):
    adapter = await get_adapter()
    user = await adapter.find_one(USERS_COLLECTION_NAME, {"uri": uri})
    return UserProfile(**user) if user is not None else None


async def set_user(userprofile: UserProfile):
    adapter = await get_adapter()
    result = await adapter.update_one(
        USERS_COLLECTION_NAME,
        {"uri": userprofile.uri},
        userprofile.model_dump(by_alias=True),
        upsert=True,
    )
    return result.inserted


async def set_template(template: PushTemplate):
    adapter = await get_adapter()
    data = template.model_dump(by_alias=True)
    data["type"] = normalise_type(template.type)
    result = await adapter.update_one(
        PUSH_TEMPLATES_COLLECTION_NAME,
        {"type": data["type"], "language": template.language},
        data,
        upsert=True,
    )
    return result.inserted


async def get_template(activity_type: str, language: str):
    adapter = await get_adapter()
    template = await adapter.find_one(
        PUSH_TEMPLATES_COLLECTION_NAME,
        {"type": normalise_type(activity_type), "language": language},
    )
    return PushTemplate(**template) if template is not None else None
