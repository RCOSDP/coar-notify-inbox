from db import get_collection
from db.models import Subscription, User


SUBSCRIPTIONS_COLLECTION_NAME = "subscriptions"
USERS_COLLECTION_NAME = "users"


class FailedToFindUser(Exception):
    pass


async def get_subscriptions_collection():
    return await get_collection(SUBSCRIPTIONS_COLLECTION_NAME)


async def get_users_collection():
    return await get_collection(USERS_COLLECTION_NAME)


async def set_subscription(subscription: Subscription) -> Subscription:
    collection = await get_subscriptions_collection()
    await collection.update_one(
        {"endpoint": subscription.endpoint},
        {"$set": subscription.model_dump(by_alias=True)},
        upsert=True
    )


async def get_subscriptions(target: str):
    collection = await get_subscriptions_collection()
    subscriptions = await (
        collection
        .find({"target": target}, {"_id": 0})
        .to_list(length=100)
    )
    return [Subscription(**subscription) for subscription in subscriptions]


async def delete_subscription(endpoint: str) -> Subscription | None:
    collection = await get_subscriptions_collection()
    subscription = await collection.find_one({"endpoint": endpoint}, {"_id": 0})
    if subscription:
        result = await collection.delete_one({"endpoint": endpoint})
        print(result.deleted_count)
        return Subscription(**subscription)
    return None


async def get_user(uri: str) -> User:
    collection = await get_users_collection()
    user = await collection.find_one({"uri": uri}, {"_id": 0})
    return user


async def set_user(user: User) -> None:
    collection = await get_users_collection()
    await collection.update_one(
        {"uri": User.uri},
        {"$set": user.model_dump(by_alias=True)},
        upsert=True
    )
