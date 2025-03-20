import json
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from config import get_settings
from db.subscriptions import set_subscription, delete_subscription
from .middleware import _logger


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
    _logger.info(f"Subscribing: {subscription.target}")
    await set_subscription(subscription)
    return Response(content=json.dumps({"status": "success"}))


@router.post("/unsubscribe")
async def unsubscribe(r: UnsubscribeRequest):
    subscription = await delete_subscription(r.endpoint)
    _logger.info(f"Unsubscribing: {subscription.target}")
    return Response(content=json.dumps({"status": "success"}))
