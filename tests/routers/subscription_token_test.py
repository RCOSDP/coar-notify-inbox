import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from routers.subscription_token import authorise, issue

SECRET = "test-secret"
TARGET = "https://example.org/users/1"
ISSUER = "https://repository.example.org"
AUDIENCE = "https://inbox.example.org"


def _request(header: str | None = None):
    request = MagicMock()
    request.headers = {"Authorization": header} if header else {}
    return request


def _settings(mock_get_settings, **overrides):
    """Set every field the module reads.

    A MagicMock answers any attribute with a truthy mock, so leaving one unset would switch a
    check on with a value no test intended.
    """
    settings = mock_get_settings.return_value
    settings.subscription_token_secret = SECRET
    settings.subscription_token_key_id = ""
    settings.subscription_token_previous_secrets = ""
    settings.subscription_token_issuer = ""
    settings.subscription_token_audience = ""

    for name, value in overrides.items():
        setattr(settings, name, value)

    return settings


@patch("routers.subscription_token.get_settings")
def test_authorise_is_skipped_when_no_secret_is_configured(mock_get_settings):
    """An existing deployment must keep working after the upgrade, loudly rather than silently."""
    _settings(mock_get_settings, subscription_token_secret="")

    authorise(_request(), TARGET)


@patch("routers.subscription_token.get_settings")
def test_authorise_accepts_a_token_for_the_same_target(mock_get_settings):
    _settings(mock_get_settings)

    authorise(_request(f"Bearer {issue(TARGET, SECRET)}"), TARGET)


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_for_another_target(mock_get_settings):
    """This is the point of the whole thing: a valid token must not work for someone else."""
    _settings(mock_get_settings)
    token = issue("https://example.org/users/2", SECRET)

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {token}"), TARGET)

    assert exc_info.value.status_code == 403


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_missing_token(mock_get_settings):
    _settings(mock_get_settings)

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_signed_with_another_secret(mock_get_settings):
    _settings(mock_get_settings)
    forged = issue(TARGET, "not-the-secret")

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {forged}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_an_expired_token(mock_get_settings):
    _settings(mock_get_settings)
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
    _settings(mock_get_settings)
    unsigned = jwt.encode({"sub": TARGET}, key="", algorithm="none")

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {unsigned}"), TARGET)

    assert exc_info.value.status_code == 401


# ---- issuer and audience ----------------------------------------------------------------------

@patch("routers.subscription_token.get_settings")
def test_authorise_accepts_a_token_with_the_expected_issuer_and_audience(mock_get_settings):
    _settings(
        mock_get_settings,
        subscription_token_issuer=ISSUER,
        subscription_token_audience=AUDIENCE,
    )

    token = issue(TARGET, SECRET, issuer=ISSUER, audience=AUDIENCE)

    authorise(_request(f"Bearer {token}"), TARGET)


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_meant_for_another_inbox(mock_get_settings):
    """The signature is right, but the token was minted to be spent somewhere else."""
    _settings(mock_get_settings, subscription_token_audience=AUDIENCE)

    token = issue(TARGET, SECRET, audience="https://other-inbox.example.org")

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {token}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_without_an_audience_when_one_is_required(mock_get_settings):
    """A secret reused for some other purpose mints tokens that carry no aud at all."""
    _settings(mock_get_settings, subscription_token_audience=AUDIENCE)

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {issue(TARGET, SECRET)}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_from_another_issuer(mock_get_settings):
    _settings(mock_get_settings, subscription_token_issuer=ISSUER)

    token = issue(TARGET, SECRET, issuer="https://elsewhere.example.org")

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {token}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_a_claim_that_is_not_configured_is_not_checked(mock_get_settings):
    """The two sides must be upgradable one at a time, in either order.

    PyJWT refuses an aud the caller did not ask about, so without verify_aud=False an inbox that
    has not been configured yet would start rejecting a repository that has.
    """
    _settings(mock_get_settings)

    token = issue(TARGET, SECRET, issuer=ISSUER, audience=AUDIENCE)

    authorise(_request(f"Bearer {token}"), TARGET)


# ---- key rotation -----------------------------------------------------------------------------

@patch("routers.subscription_token.get_settings")
def test_authorise_accepts_a_token_signed_with_the_current_named_key(mock_get_settings):
    _settings(mock_get_settings, subscription_token_key_id="2026-09")

    token = issue(TARGET, SECRET, key_id="2026-09")

    authorise(_request(f"Bearer {token}"), TARGET)


@patch("routers.subscription_token.get_settings")
def test_authorise_accepts_a_token_signed_with_a_retired_key(mock_get_settings):
    """The window that makes a rotation two restarts instead of a flag day."""
    _settings(
        mock_get_settings,
        subscription_token_key_id="2026-09",
        subscription_token_previous_secrets='{"2026-06": "the-old-secret"}',
    )

    token = issue(TARGET, "the-old-secret", key_id="2026-06")

    authorise(_request(f"Bearer {token}"), TARGET)


@patch("routers.subscription_token.get_settings")
def test_authorise_rejects_a_token_naming_a_key_that_is_no_longer_accepted(mock_get_settings):
    _settings(mock_get_settings, subscription_token_key_id="2026-09")

    token = issue(TARGET, "the-old-secret", key_id="2026-01")

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {token}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_a_token_naming_no_key_is_checked_against_all_of_them(mock_get_settings):
    """A caller that predates kids sends none, and must still be verified during a rotation."""
    _settings(
        mock_get_settings,
        subscription_token_key_id="2026-09",
        subscription_token_previous_secrets='{"2026-06": "the-old-secret"}',
    )

    authorise(_request(f"Bearer {issue(TARGET, 'the-old-secret')}"), TARGET)


@patch("routers.subscription_token.get_settings")
def test_a_retired_key_cannot_shadow_the_current_one(mock_get_settings):
    """Leaving a stale entry behind under the current kid must not resurrect the old secret."""
    _settings(
        mock_get_settings,
        subscription_token_key_id="2026-09",
        subscription_token_previous_secrets='{"2026-09": "the-old-secret"}',
    )

    authorise(_request(f"Bearer {issue(TARGET, SECRET, key_id='2026-09')}"), TARGET)

    with pytest.raises(HTTPException) as exc_info:
        authorise(_request(f"Bearer {issue(TARGET, 'the-old-secret', key_id='2026-09')}"), TARGET)

    assert exc_info.value.status_code == 401


@patch("routers.subscription_token.get_settings")
def test_an_unreadable_list_of_retired_keys_does_not_take_the_inbox_down(mock_get_settings):
    """It only matters mid-rotation, and the current key still has to work."""
    _settings(mock_get_settings, subscription_token_previous_secrets="not json")

    authorise(_request(f"Bearer {issue(TARGET, SECRET)}"), TARGET)


@patch("routers.subscription_token.get_settings")
def test_no_retired_keys_is_spelled_as_an_empty_value(mock_get_settings):
    """Emptying the setting is the last step of a rotation, so it cannot be a parse error."""
    _settings(mock_get_settings, subscription_token_previous_secrets="   ")

    authorise(_request(f"Bearer {issue(TARGET, SECRET)}"), TARGET)
