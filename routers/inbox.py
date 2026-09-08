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
    create_notification,
    get_notification,
    get_notifications,
    get_notifications_collection,
)
from tasks.webhooks import send_notification_to_webhook


router = APIRouter(
    prefix="/inbox",
    tags=["inbox"],
)


def get_inbox_url(request: Request) -> str:
    return str(request.base_url) + "inbox"


def build_page_url(base_url: str, page: int, page_size: int) -> str:
    return f"{base_url}?{urlencode({'page': page, 'page_size': page_size})}"


def build_page_links(base_url: str, page: int, page_size: int, total: int) -> list[str]:
    links = []
    if page > 1:
        links.append(f'<{build_page_url(base_url, page - 1, page_size)}>; rel="prev"')
    if page * page_size < total:
        links.append(f'<{build_page_url(base_url, page + 1, page_size)}>; rel="next"')
    return links


def get_notification_links(notifications: list[Notification], base_url: str) -> list[str]:
    return [f"{base_url}{notification['id']}" for notification in notifications]


@router.options("/", include_in_schema=False)
@router.options("")
async def read_inbox_options():
    return Response(headers={"Accept-Post": "application/ld+json"})


@router.get("/", include_in_schema=False)
@router.get("")
async def read_inbox(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(PAGE_LIMIT, ge=1),
) -> JSONResponse:
    inbox_url = get_inbox_url(request)
    notifications = await get_notifications(page=page, page_size=page_size)
    collection = await get_notifications_collection()
    total = await collection.count_documents({})

    headers = {"content-type": "application/ld+json"}
    links = build_page_links(inbox_url, page, page_size, total)
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
                           payload: dict = Body(...)):
    notification = Notification(**payload)

    notification_id = await create_notification(notification)

    if notification_id and get_settings().on_receive_notification_webhook_url:
        background_tasks.add_task(
            send_notification_to_webhook,
            notification,
            get_settings().on_receive_notification_webhook_url,
        )

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

    raise HTTPException(status_code=404, detail="Notification not found")
