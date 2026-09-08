import json
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import JSONResponse

from config import PAGE_LIMIT, get_settings
from db.models import Notification
from db.notifications import (
    count_notifications,
    create_notification,
    get_notification,
    get_notifications,
)
from services.push import send_webpush
from tasks.webhooks import send_notification_to_webhook


router = APIRouter(
    prefix="/inbox",
    tags=["inbox"],
)


def get_inbox_url(request: Request) -> str:
    return str(request.base_url) + "inbox"


def get_notification_links(notifications: list[Notification], base_url: str) -> list[str]:
    return [f"{base_url}/{notification['id']}" for notification in notifications]


def build_page_url(base_url: str, page: int, page_size: int, target: str | None) -> str:
    query = {"page": page, "page_size": page_size}
    if target:
        query["target"] = target
    return f"{base_url}?{urlencode(query)}"


@router.options("/", include_in_schema=False)
@router.options("")
async def read_inbox_options():
    return Response(headers={"Accept-Post": "application/ld+json"})


@router.get("/", include_in_schema=False)
@router.get("")
async def read_inbox(
    request: Request,
    target: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(PAGE_LIMIT, ge=1),
) -> JSONResponse:
    inbox_url = get_inbox_url(request)
    notifications = await get_notifications(
        page=page, page_size=page_size, target=target
    )
    total = await count_notifications({"target.id": target} if target else {})

    # The listing was capped at the first PAGE_LIMIT notifications with no way to reach the rest:
    # the HTML index took page/page_size but this endpoint did not, so a consumer could not see
    # anything older. The body keeps its shape, and paging is advertised with Link headers
    # (RFC 8288), which is what a machine client can follow without parsing the payload.
    headers = {"content-type": "application/ld+json"}
    links = []
    if page > 1:
        links.append(
            f'<{build_page_url(inbox_url, page - 1, page_size, target)}>; rel="prev"'
        )
    if page * page_size < total:
        links.append(
            f'<{build_page_url(inbox_url, page + 1, page_size, target)}>; rel="next"'
        )
    if links:
        headers["Link"] = ", ".join(links)

    return JSONResponse(
        headers=headers,
        content={
            "@context": "http://www.w3.org/ns/ldp",
            "@id": inbox_url,
            "contains": get_notification_links(notifications, base_url=inbox_url),
        },
    )


@router.post("/", include_in_schema=False)
@router.post("")
async def add_notification(request: Request, background_tasks: BackgroundTasks,
                           notification: Notification = Body(...)):
    if await get_notification(notification.id) is not None:
        raise HTTPException(
            status_code=409,
            detail="ID conflict: notification with this ID already exists.",
        )

    notification_id = await create_notification(notification)

    if notification_id and get_settings().on_receive_notification_webhook_url:
        background_tasks.add_task(
            send_notification_to_webhook,
            notification,
            get_settings().on_receive_notification_webhook_url,
        )

    if notification_id and get_settings().enable_push_notifications:
        background_tasks.add_task(send_webpush, notification)

    return Response(
        headers={"Location": f"{get_inbox_url(request)}/{notification_id}"},
        status_code=201,
    )


@router.get("/{notification_id}", response_model=Notification)
async def read_notification(notification_id: str):
    notification = await get_notification(notification_id)

    if notification:
        return Response(
            headers={"content-type": "application/ld+json"},
            content=json.dumps(notification, default=str),
        )

    raise HTTPException(status_code=404, detail="Notification not found.")
