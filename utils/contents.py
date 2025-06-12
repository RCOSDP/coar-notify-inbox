import re

from db.models import Notification, UserProfile
from db.subscriptions import get_template
from utils import dt2idt


async def make_contents(
    notification: Notification, user: UserProfile
) -> tuple[str, str, str]:
    params = make_params(notification, user)

    title, body, url = "", "", ""
    template = await get_template(notification.type, user.language)

    if not template:
        template = await get_template(notification.type, "en")

    if not template:
        return title, body, url

    title = render(template.title, params)
    body = render(template.body, params)
    url = params["context_uri"] or params["object_uri"]

    return title, body, url


def render(template: str, data: dict):
    pattern = r"\{\{\s*(\w+)\s*\}\}"
    return re.sub(pattern, lambda match: str(data.get(match.group(1), "")), template)


def make_params(
    notification: Notification, user: UserProfile
) -> dict[str, str | None]:
    params = {
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
