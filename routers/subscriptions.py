from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from config import get_settings
from db.models import PushTemplate
from db.subscriptions import (
    delete_subscription,
    get_subscription,
    set_subscription,
    set_template,
    set_user,
)
from utils import logger

from .inbox import router as inbox_router
from .middleware import admin_only
from .subscription_token import authorise


router = APIRouter(
    tags=["subscription"],
)


class SubscribeRequest(BaseModel):
    target: str
    endpoint: str
    expiration_time: str | None = Field(alias="expirationTime", default=None)
    keys: dict[str, str] = None


class UnsubscribeRequest(BaseModel):
    endpoint: str


class UserProfileRequest(BaseModel):
    uri: str
    displayname: str | None = None
    language: str | None = None
    timezone: str | None = None


@inbox_router.get("/subscription/vapid-public-key")
async def get_vapid_public_key():
    return Response(content=get_settings().vapid_public_key)


@router.post("/subscribe")
async def subscribe(request: Request, subscription: SubscribeRequest):
    # A subscription decides where someone's notifications go, so the caller has to prove the
    # repository authenticated that target - knowing the URI is not enough.
    authorise(request, subscription.target)

    if await set_subscription(subscription):
        logger.info(
            f"Subscribing: {subscription.target}, "
            f"endpoint: {subscription.endpoint[:24]}..."
        )
        return Response(status_code=201)
    logger.info(
        f"Aleady subscribed: {subscription.target}, "
        f"endpoint: {subscription.endpoint[:24]}..."
    )

    return Response(status_code=200)


@router.post("/unsubscribe")
async def unsubscribe(request: Request, r: UnsubscribeRequest):
    # The request carries only an endpoint, so the target to authorise against comes from the
    # stored subscription. A caller who cannot act for that target cannot remove it.
    existing = await get_subscription(r.endpoint)
    if existing is not None:
        authorise(request, existing.target)

    count = await delete_subscription(r.endpoint)
    if count == 0:
        logger.warning(f"Subscription not found: {r.endpoint[:24]}...")
        raise HTTPException(
            status_code=404,
            detail="Subscription not found",
            )
    logger.info(
        f"Unsubscribing: {r.endpoint[:24]}..."
    )
    return Response(status_code=200)


@router.post("/userprofile")
async def user_profile(request: Request, user: UserProfileRequest):
    # The profile picks the language a push is rendered in, so it is authorised the same way.
    authorise(request, user.uri)

    if await set_user(user):
        logger.info(f"Setting user profile: {user.uri}")
        return Response(status_code=201)
    return Response(status_code=200)


@router.post("/push-template")
@admin_only
# pylint: disable=unused-argument
async def update_template(request: Request, template: PushTemplate):
    if await set_template(template):
        logger.info(f"Setting template: {template.name}, {template.language}")
        return Response(status_code=201)
    return Response(status_code=200)
