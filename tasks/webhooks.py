import requests

from db.models import Notification
from utils import logger


def send_notification_to_webhook(notification: Notification, webhook_url: str) -> None:
    try:
        response = requests.post(
            url=webhook_url,
            headers={"content-type": "application/ld+json"},
            # json= takes the object to serialise, not a string. Passing a string sent a
            # JSON-encoded string, and json.dumps(default=str) on a Pydantic model stringified
            # it with repr(), so the receiver got something like
            #   "id='urn:uuid:1' updated=datetime.datetime(...) at_context=[...]"
            # which is valid JSON but not the notification. mode="json" renders the datetimes,
            # and by_alias keeps "@context" and "ietf:cite-as".
            json=notification.model_dump(by_alias=True, mode="json"),
            timeout=(10, 10),
        )

        response.raise_for_status()

        logger.info(f"Successfully sent notification to {webhook_url}. "
                    f"Status code: {response.status_code}")
    except requests.RequestException:
        logger.exception(f"Failed to send notification to {webhook_url}")
