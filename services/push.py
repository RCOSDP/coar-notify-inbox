import json
from pywebpush import webpush, WebPushException

from config import get_settings
from db.models import Subscription, Notification, User
from db.subscriptions import delete_subscription, get_subscriptions, get_user

from routers.middleware import _logger

def send(subscription: Subscription, payload: dict):
    webpush(
        subscription_info=subscription,
        data=json.dumps(payload),
        vapid_private_key=get_settings().vapid_private_key,
        vapid_claims={"sub": get_settings().subscriber}
    )


async def send_webpush(notification: Notification):
    target_uri = notification.target.id
    subscriptions = await get_subscriptions(target_uri)
    user = await get_user(target_uri)

    title, body, url = make_push_contents(notification, user)

    payload = {
        "title": title,
        "options": {
            "body": body,
            "tag": notification.id,
            "icon": get_settings().icon,
            "badge": get_settings().icon,
            "requireInteraction": False,
            "data": {
                "url": url
            }
        }
    }

    for subscription in subscriptions:
        try:
            send(subscription, payload)
        except WebPushException as ex:
            _logger.error(f"Failed to send notification to {target_uri}: {ex}")
            if ex.response is not None and ex.response.status_code in [404, 410]:
                await delete_subscription(subscription.endpoint)


def make_push_contents(notification: Notification, user:User) -> tuple[str, str, str]:
    return "test", "test", "test"
