from db import get_adapter
from db.models import Subscription, UserProfile, PushTemplate
from utils import logger


SUBSCRIPTIONS_COLLECTION_NAME = "subscriptions"
USERS_COLLECTION_NAME = "userprofiles"
PUSH_TEMPLATES_COLLECTION_NAME = "push_templates"


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
    result = await adapter.update_one(
        PUSH_TEMPLATES_COLLECTION_NAME,
        {"type": template.type, "language": template.language},
        template.model_dump(by_alias=True),
        upsert=True,
    )
    return result.inserted


async def get_template(activity_type: str, language: str):
    adapter = await get_adapter()
    template = await adapter.find_one(
        PUSH_TEMPLATES_COLLECTION_NAME,
        {"type": activity_type, "language": language},
    )
    return PushTemplate(**template) if template is not None else None
