import json
import traceback
from pywebpush import webpush, WebPushException

from config import get_settings
from db.models import Subscription, Notification, UserProfile
from db.subscriptions import (
    delete_subscriptions, get_subscriptions, get_template, get_user
)
from utils import dt2idt


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
            if ex.response is not None and ex.response.status_code in [404, 410]:
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


async def make_contents(notification: Notification, user: UserProfile) -> tuple[str, str, str]:
    params = make_params(notification, user)

    title, body, url = "", "", ""
    template = await get_template(notification.type, user.language)

    if not template:
        template = await get_template(notification.type, "en")

    if not template:
        return title, body, url

    title = template.title.replace("{{ ", "{").replace(" }}", "}").format(**params)
    body = template.body.replace("{{ ", "{").replace(" }}", "}").format(**params)
    url = params["context_uri"] or params["object_uri"]

    return title, body, url


def make_params(notification: Notification, user: UserProfile):
    params:  dict[str, str | None] = {
        "timestamp": dt2idt(notification.updated).rfc3339format(),
        "target_uri": notification.target.id,
        "object_uri": notification.object.id,
        "object_name": notification.object.name,
        "context_uri": notification.context.id if notification.context else None,
        "actor_uri": notification.actor.id if notification.actor else None,
        "actor_name": notification.actor.name if notification.actor else "Unknown",
        "target_name": user.displayname or "Unknown",
    }
    return params
