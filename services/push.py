import json
import traceback
from pywebpush import webpush, WebPushException

from config import get_settings
from db.models import Subscription, Notification, UserProfile
from db.subscriptions import delete_subscriptions, get_subscriptions, get_user
from utils import logger
from utils.contents import make_contents


def send(subscription: Subscription, payload: dict):
    webpush(
        subscription_info=subscription.model_dump(by_alias=True),
        data=json.dumps(payload),
        vapid_private_key=get_settings().vapid_private_key,
        vapid_claims={"sub": get_settings().subscriber}
    )


async def send_webpush(notification: Notification):
    target_uri = notification.target.id
    subscriptions = await get_subscriptions(target_uri)

    if not subscriptions:
        return None

    user = await get_user(target_uri)
    payload = await make_payload(notification, user)

    not_sent = []
    for subscription in subscriptions:
        try:
            send(subscription, payload)
        except WebPushException as ex:
            traceback.print_exc()
            if ex.response is not None:
                logger.error(ex.response.json())
                if ex.response.status_code in [404, 410]:
                    not_sent.append(subscription.endpoint)

    return await delete_subscriptions(not_sent) if not_sent else None


async def make_payload(notification: Notification, user: UserProfile) -> dict:
    title, body, url = await make_contents(notification, user)

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
    return payload
