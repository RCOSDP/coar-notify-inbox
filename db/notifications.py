from config import PAGE_LIMIT
from db import get_adapter
from db.models import Notification


NOTIFICATIONS_COLLECTION_NAME = "notifications"
NOTIFICATION_STATES_COLLECTION_NAME = "notification_states"

DESCENDING = -1


class FailedToFindNotificationState(Exception):
    pass


async def create_notification(notification: Notification) -> str:
    adapter = await get_adapter()
    await adapter.insert_one(
        NOTIFICATIONS_COLLECTION_NAME, notification.model_dump(by_alias=True)
    )
    await adapter.insert_one(
        NOTIFICATION_STATES_COLLECTION_NAME, {"id": notification.id, "read": False}
    )
    return notification.id


async def get_notification(notification_id: str) -> Notification:
    adapter = await get_adapter()
    return await adapter.find_one(NOTIFICATIONS_COLLECTION_NAME, {"id": notification_id})


async def get_notifications(
        page: int = 1, page_size: int = PAGE_LIMIT, target: str = None
) -> list[Notification]:
    adapter = await get_adapter()
    query = {"target.id": target} if target else {}
    return await adapter.find(
        NOTIFICATIONS_COLLECTION_NAME,
        query,
        sort=("updated", DESCENDING),
        skip=(page - 1) * page_size,
        limit=page_size,
    )


async def delete_notification(notification_id) -> None:
    adapter = await get_adapter()
    await adapter.delete_one(NOTIFICATIONS_COLLECTION_NAME, {"id": notification_id})


async def get_notification_state_ids_by_status(read: bool) -> list[str]:
    adapter = await get_adapter()
    states = await adapter.find(
        NOTIFICATION_STATES_COLLECTION_NAME, {"read": read}, limit=PAGE_LIMIT
    )
    return [state["id"] for state in states]


async def update_notification_state(notification_id: str, read: bool) -> None:
    adapter = await get_adapter()
    result = await adapter.update_one(
        NOTIFICATION_STATES_COLLECTION_NAME, {"id": notification_id}, {"read": read}
    )
    if result.matched == 0:
        raise FailedToFindNotificationState(
            f"Could not find notification state for notification {notification_id}"
        )


async def count_notifications(db_filter: dict = None) -> int:
    adapter = await get_adapter()
    return await adapter.count(NOTIFICATIONS_COLLECTION_NAME, db_filter or {})
