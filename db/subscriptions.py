from db import get_collection
from db.models import Subscription, UserProfile, PushTemplate
from utils import logger

SUBSCRIPTIONS_COLLECTION_NAME = "subscriptions"
USERS_COLLECTION_NAME = "userprofiles"
PUSH_TEMPLATES_COLLECTION_NAME = "push_templates"


async def get_subscriptions_collection():
    return await get_collection(SUBSCRIPTIONS_COLLECTION_NAME)


async def get_users_collection():
    return await get_collection(USERS_COLLECTION_NAME)


async def get_push_templates_collection():
    return await get_collection(PUSH_TEMPLATES_COLLECTION_NAME)


async def set_subscription(subscription: Subscription):
    collection = await get_subscriptions_collection()
    result = await collection.update_one(
        {"endpoint": subscription.endpoint},
        {"$set": subscription.model_dump(by_alias=True)},
        upsert=True
    )
    return result.upserted_id


async def get_subscriptions(target: str):
    collection = await get_subscriptions_collection()
    subscriptions = await (
        collection
        .find({"target": target}, {"_id": 0})
        .to_list(length=100)
    )
    return [Subscription(**subscription) for subscription in subscriptions]


async def delete_subscription(endpoint: str) -> int:
    collection = await get_subscriptions_collection()
    result = await collection.delete_one({"endpoint": endpoint})
    return result.deleted_count


async def delete_subscriptions(endpoints: list[str]):
    collection = await get_subscriptions_collection()
    await collection.delete_many({"endpoint": {"$in": endpoints}})
    logger.info(f"Deleted {len(endpoints)} subscriptions")


async def get_user(uri: str):
    collection = await get_users_collection()
    user = await collection.find_one({"uri": uri}, {"_id": 0})

    return UserProfile(**user) if user is not None else None


async def set_user(userprofile: UserProfile):
    collection = await get_users_collection()
    result = await collection.update_one(
        {"uri": userprofile.uri},
        {"$set": userprofile.model_dump(by_alias=True)},
        upsert=True
    )
    return result.upserted_id


async def set_template(template: PushTemplate) -> None:
    collection = await get_push_templates_collection()
    result = await collection.update_one(
        {"type": template.type, "language": template.language},
        {"$set": template.model_dump(by_alias=True)},
        upsert=True
    )
    return result.upserted_id


async def get_template(activity_type: str, language: str):
    collection = await get_push_templates_collection()
    template = await collection.find_one(
        {"type": activity_type, "language": language},
        {"_id": 0}
    )
    return PushTemplate(**template) if template is not None else None
