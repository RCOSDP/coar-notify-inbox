"""Proof that the caller may act for a given target.

Registering a subscription is what decides where a person's notifications are delivered, so it
must not be enough to know their target URI - those are predictable (a repository typically
derives them from a user id). Without this, anyone who can reach the inbox could point another
person's notifications at their own push endpoint.

The repository signs a short-lived token naming the target it has just authenticated, and the
inbox only accepts a subscription when the token says so. The inbox never has to know how the
repository authenticates people; it only has to trust the signature.

    Authorization: Bearer <JWT>
    claims: {"sub": "<target uri>", "exp": ..., "iat": ...}

SUBSCRIPTION_TOKEN_SECRET is the shared secret. Leaving it empty keeps the previous behaviour -
the endpoints stay open - and logs a warning, so an existing deployment does not break on
upgrade; set it on both sides to close the hole.
"""
import time

import jwt
from fastapi import HTTPException, Request

from config import get_settings
from utils import logger

ALGORITHM = "HS256"
_BEARER = "Bearer "


def issue(target: str, secret: str, ttl_seconds: int = 300) -> str:
    """Mint a token for a target. Provided so a caller does not have to hand-roll the claims."""
    now = int(time.time())
    return jwt.encode(
        {"sub": target, "iat": now, "exp": now + ttl_seconds}, secret, algorithm=ALGORITHM
    )


def claims_from(request: Request) -> dict | None:
    """Return the verified claims, or None when verification is switched off."""
    secret = get_settings().subscription_token_secret

    if not secret:
        logger.warning(
            "SUBSCRIPTION_TOKEN_SECRET is not set: the subscription endpoints accept any caller, "
            "so anyone who can reach this inbox can redirect another target's notifications"
        )
        return None

    header = request.headers.get("Authorization", "")
    if not header.startswith(_BEARER):
        raise HTTPException(status_code=401, detail="Missing subscription token")

    try:
        return jwt.decode(header[len(_BEARER):], secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as ex:
        # The reason is deliberately not echoed back: expired and forged tokens look the same
        # from outside, and the detail is in the log for whoever runs the inbox.
        logger.warning("Rejected subscription token: %s", ex)
        raise HTTPException(status_code=401, detail="Invalid subscription token") from ex


def authorise(request: Request, target: str) -> None:
    """Raise unless the caller holds a token for this target."""
    claims = claims_from(request)

    if claims is None:
        return

    if claims.get("sub") != target:
        logger.warning(
            "Subscription token for %s cannot act for %s", claims.get("sub"), target
        )
        raise HTTPException(
            status_code=403, detail="The token does not authorise this target"
        )
