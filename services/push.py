import json
from pywebpush import webpush, WebPushException
from starlette.concurrency import run_in_threadpool

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

    if payload is None:
        logger.warning(
            "No push template for type=%s language=%s; nothing sent for %s",
            notification.type,
            getattr(user, "language", None),
            notification.id,
        )
        return None

    not_sent = []
    for subscription in subscriptions:
        try:
            # webpush() blocks on network IO. This coroutine runs on the event loop (it is
            # scheduled as a BackgroundTask), so calling it directly would stall every other
            # request for the duration of each push.
            await run_in_threadpool(send, subscription, payload)
        except WebPushException as ex:
            logger.exception("Push failed for %s", subscription.endpoint[:24])
            if ex.response is not None:
                logger.error(ex.response.json())
                if ex.response.status_code in [404, 410]:
                    not_sent.append(subscription.endpoint)
        except (ValueError, TypeError, KeyError):
            # A malformed subscription - a key that is not valid base64, say - raises before any
            # request is made, and no retry can fix it. pywebpush surfaces that as binascii.Error
            # (a ValueError), which is not a WebPushException, so without this the loop would stop
            # here and every later subscriber would silently miss the notification.
            logger.exception(
                "Dropping malformed subscription %s", subscription.endpoint[:24]
            )
            not_sent.append(subscription.endpoint)
        except Exception:  # pylint: disable=broad-exception-caught
            # Anything else is treated as transient: keep the subscription and keep going, so one
            # failure cannot deprive the remaining subscribers.
            logger.exception("Push failed for %s", subscription.endpoint[:24])

    return await delete_subscriptions(not_sent) if not_sent else None


async def make_payload(notification: Notification, user: UserProfile) -> dict | None:
    """Build the Web Push payload, or None when there is no template to render.

    make_contents() yields empty strings when no template matches, and a notification with an
    empty title reaches the browser as a blank banner, so that case must not be sent.
    """
    title, body, url = await make_contents(notification, user)

    if not title:
        return None

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
