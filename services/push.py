import json
import traceback
from pywebpush import webpush, WebPushException

from config import get_settings
from db.models import Subscription, Notification, User
from db.subscriptions import delete_subscriptions, get_subscriptions, get_user


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
    user = await get_user(target_uri)

    title, body, url = make_contents(notification, user)

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

    not_sent = []
    for subscription in subscriptions:
        try:
            send(subscription, payload)
        except WebPushException as ex:
            traceback.print_exc()
            if ex.response is not None and ex.response.status_code in [404, 410]:
                not_sent.append(subscription.endpoint)

    await delete_subscriptions(not_sent)


def make_contents(notification: Notification, user: User) -> tuple[str, str, str]:
    params = {
        "updated": notification.updated,
        "target_uri": notification.target.id,
        "object_uri": notification.object.id,
        "object_name": notification.object.name,
        "context_uri": notification.context.id,
        "actor_uri": notification.actor.id,
        "actor_name": notification.actor.name,
        "user_name": user.displayname if user is not None else "Unknown",
    }
    activity_type = notification.type

    title, body, url = "", "", ""

    if activity_type == ["Announce", "coar-notify:IngestAction"]:
        title = "Your item has been registered"
        body = "\"{object_name}\" has been registered by {actor_name}".format(
            **params
        )
        url = params["object_uri"]
    elif activity_type == ["Offer", "coar-notify:EndorsementAction"]:
        title = "You have received a request."
        body = "{object_name} has been requested by {actor_name}".format(
            **params
        )
        url = params["context_uri"]
    elif activity_type == ["Announce", "coar-notify:EndorsementAction"]:
        title = "Your item has been approved"
        body = "{object_name} has been approved by {actor_name}".format(
            **params
        )
        url = params["object_uri"]
    elif activity_type == ["Reject"]:
        title = "Your item has been rejected"
        body = "{object_name} has been rejected by {actor_name}".format(
            **params
        )
        url = params["context_uri"]

    return title, body, url
