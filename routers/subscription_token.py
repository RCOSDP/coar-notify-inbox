"""Proof that the caller may act for a given target.

Registering a subscription is what decides where a person's notifications are delivered, so it
must not be enough to know their target URI - those are predictable (a repository typically
derives them from a user id). Without this, anyone who can reach the inbox could point another
person's notifications at their own push endpoint.

The repository signs a short-lived token naming the target it has just authenticated, and the
inbox only accepts a subscription when the token says so. The inbox never has to know how the
repository authenticates people; it only has to trust the signature.

    Authorization: Bearer <JWT>
    header: {"alg": "HS256", "kid": "<key name>"}
    claims: {"sub": "<target uri>", "iss": ..., "aud": ..., "exp": ..., "iat": ...}

SUBSCRIPTION_TOKEN_SECRET is the shared secret. Leaving it empty keeps the previous behaviour -
the endpoints stay open - and logs a warning, so an existing deployment does not break on
upgrade; set it on both sides to close the hole.

Three things narrow what a signature alone proves:

- SUBSCRIPTION_TOKEN_ISSUER and SUBSCRIPTION_TOKEN_AUDIENCE, when set, are required to match. A
  shared secret is symmetric, so anything else holding it can mint tokens; naming who may issue
  one and which inbox it is for means a secret that gets reused elsewhere, or a token meant for a
  different inbox, is not silently good here.
- SUBSCRIPTION_TOKEN_KEY_ID names the current key in the token's "kid" header, and
  SUBSCRIPTION_TOKEN_PREVIOUS_SECRETS holds the keys that still verify, as the JSON object
  {"kid": "secret"}. Rotating is then two restarts rather than a flag day. A token with no kid is
  checked against every accepted key, which is what a repository that predates this sends.
"""
import json
import time

import jwt
from fastapi import HTTPException, Request

from config import get_settings
from utils import logger

ALGORITHM = "HS256"
_BEARER = "Bearer "


def issue(target: str, secret: str, ttl_seconds: int = 300, *, key_id: str = "",
          issuer: str = "", audience: str = "") -> str:
    """Mint a token for a target. Provided so a caller does not have to hand-roll the claims."""
    now = int(time.time())
    claims = {"sub": target, "iat": now, "exp": now + ttl_seconds}

    if issuer:
        claims["iss"] = issuer
    if audience:
        claims["aud"] = audience

    return jwt.encode(
        claims, secret, algorithm=ALGORITHM,
        headers={"kid": key_id} if key_id else None,
    )


def previous_secrets(settings) -> dict[str, str]:
    """The retired keys, or none when the setting is empty or malformed."""
    raw = (settings.subscription_token_previous_secrets or "").strip()

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except ValueError as ex:
        parsed = None
        logger.warning("SUBSCRIPTION_TOKEN_PREVIOUS_SECRETS is not valid JSON (%s)", ex)

    if not isinstance(parsed, dict):
        # Refusing to start would take the inbox down over a value that only matters while a
        # rotation is in flight; tokens signed with the current key keep working either way.
        logger.warning(
            "SUBSCRIPTION_TOKEN_PREVIOUS_SECRETS is ignored: it must be a JSON object of "
            "key id to secret"
        )
        return {}

    return {str(kid): str(secret) for kid, secret in parsed.items()}


def accepted_keys(settings) -> dict[str | None, str]:
    """Every key a token may be signed with, by kid. The current one is first."""
    keys: dict[str | None, str] = {
        settings.subscription_token_key_id or None: settings.subscription_token_secret
    }
    # setdefault, not update: a stale entry naming the current kid must not shadow the key that is
    # actually in use, and the current key is tried first when a token names none.
    for kid, secret in previous_secrets(settings).items():
        keys.setdefault(kid, secret)
    return keys


def _rejected(reason: object) -> HTTPException:
    # The reason is deliberately not echoed back: expired, forged and misaddressed tokens look the
    # same from outside, and the detail is in the log for whoever runs the inbox.
    logger.warning("Rejected subscription token: %s", reason)
    return HTTPException(status_code=401, detail="Invalid subscription token")


def _decode(token: str, settings) -> dict:
    """Verify against the key the token names, or against all of them when it names none."""
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.PyJWTError as ex:
        raise _rejected(ex) from ex

    keys = accepted_keys(settings)
    if kid is None:
        candidates = list(keys.values())
    elif kid in keys:
        candidates = [keys[kid]]
    else:
        raise _rejected(f"unknown key id {kid!r}")

    claims = {}
    if settings.subscription_token_issuer:
        claims["issuer"] = settings.subscription_token_issuer
    if settings.subscription_token_audience:
        claims["audience"] = settings.subscription_token_audience
    else:
        # PyJWT refuses a token that carries an aud when the caller names none, which would make
        # an inbox that has not been configured yet reject the repository the moment it starts
        # sending one. "Not configured" has to mean "not checked", or the two sides could only be
        # upgraded together.
        claims["options"] = {"verify_aud": False}

    for secret in candidates:
        try:
            return jwt.decode(token, secret, algorithms=[ALGORITHM], **claims)
        except jwt.InvalidSignatureError:
            # Only the signature is worth retrying with another key: an expired or misaddressed
            # token is no better under the next one, and trying anyway hides why it was refused.
            continue
        except jwt.PyJWTError as ex:
            raise _rejected(ex) from ex

    raise _rejected("no accepted key verifies the signature")


def claims_from(request: Request) -> dict | None:
    """Return the verified claims, or None when verification is switched off."""
    settings = get_settings()

    if not settings.subscription_token_secret:
        logger.warning(
            "SUBSCRIPTION_TOKEN_SECRET is not set: the subscription endpoints accept any caller, "
            "so anyone who can reach this inbox can redirect another target's notifications"
        )
        return None

    header = request.headers.get("Authorization", "")
    if not header.startswith(_BEARER):
        raise HTTPException(status_code=401, detail="Missing subscription token")

    return _decode(header[len(_BEARER):], settings)


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
