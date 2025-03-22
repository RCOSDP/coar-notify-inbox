from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from config import get_settings
from db.subscriptions import set_subscription, delete_subscription
from utils import logger


router = APIRouter(
    prefix="/inbox",
    tags=["subscription"],
)


class SubscribeRequest(BaseModel):
    target: str
    endpoint: str
    expiration_time: str | None = Field(alias="expirationTime", default=None)
    keys: dict[str, str] = None


class UnsubscribeRequest(BaseModel):
    endpoint: str


@router.get("/subscription/vapid-public-key")
async def get_vapid_public_key():
    return Response(content=get_settings().vapid_public_key)


@router.post("/subscribe")
async def subscribe(subscription: SubscribeRequest):
    logger.info(
        f"Subscribing: {subscription.target}, "
        f"endpoint: {subscription.endpoint[:24]}..."
    )
    await set_subscription(subscription)
    return Response(status_code=201)


@router.post("/unsubscribe")
async def unsubscribe(r: UnsubscribeRequest):
    subscription = await delete_subscription(r.endpoint)
    if subscription is None:
        logger.warning(f"Subscription not found: {r.endpoint[:24]}...")
        raise HTTPException(
            status_code=404,
            detail="Subscription not found",
            )
    logger.info(
        f"Unsubscribing: {subscription.target}"
        f"endpoint: {subscription.endpoint[:24]}..."
    )
    return Response(status_code=204)
