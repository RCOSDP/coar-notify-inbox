import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from routers.subscription_token import authorise, issue

SECRET = "test-secret"
TARGET = "https://example.org/users/1"


def _request(header: str | None = None):
    request = MagicMock()
    request.headers = {"Authorization": header} if header else {}
    return request


@patch("routers.subscription_token.get_settings")
def test_authorise_is_skipped_when_no_secret_is_configured(mock_get_settings):
    """An existing deployment must keep working after the upgrade, loudly rather than silently."""
    mock_get_settings.return_value.subscription_token_secret = ""

    authorise(_request(), TARGET)


@patch("routers.subscription_token.get_settings")
def test_authorise_accepts_a_token_for_the_same_target(mock_get_settings):
    mock_get_settings.return_value.subscription_token_secret = SECRET

    authorise(_request(f"Bearer {issue(TARGET, SECRET)}"), TARGET)


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_for_another_target(mock_get_settings):
    """This is the point of the whole thing: a valid token must not work for someone else."""
    mock_get_settings.return_value.subscription_token_secret = SECRET
    token = issue("https://example.org/users/2", SECRET)

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {token}"), TARGET)

    assert exc_info.value.status_code == 403


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_missing_token(mock_get_settings):
    mock_get_settings.return_value.subscription_token_secret = SECRET

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_signed_with_another_secret(mock_get_settings):
    mock_get_settings.return_value.subscription_token_secret = SECRET
    forged = issue(TARGET, "not-the-secret")

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {forged}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_an_expired_token(mock_get_settings):
    mock_get_settings.return_value.subscription_token_secret = SECRET
    now = int(time.time())
    expired = jwt.encode(
        {"sub": TARGET, "iat": now - 600, "exp": now - 300}, SECRET, algorithm="HS256"
    )

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {expired}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_an_unsigned_token(mock_get_settings):
    """alg=none must not be accepted, which is why decode() pins the algorithm."""
    mock_get_settings.return_value.subscription_token_secret = SECRET
    unsigned = jwt.encode({"sub": TARGET}, key="", algorithm="none")

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {unsigned}"), TARGET)

    assert exc_info.value.status_code == 401
