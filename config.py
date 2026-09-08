from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

PAGE_LIMIT = 50


class Settings(BaseSettings):
    allowed_admin_origins: set[str] = set()
    allowed_origins: set[str] = set()
    mongo_db_uri: str = ""
    mongo_db_name: str = ""
    on_receive_notification_webhook_url: str = ""

    enable_push_notifications: bool = True
    subscriber: str = "mailto:"
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    icon: str = ""
    # Shared secret the repository signs subscription tokens with. Empty keeps the
    # subscription endpoints open, as they were before tokens existed.
    subscription_token_secret: str = ""
    # The name of that secret, carried in the token's "kid" header. Naming the key is what makes a
    # rotation possible without a flag day: the inbox can tell which key a token was signed with
    # instead of having to guess. Empty stamps no kid, which is what a caller that predates this
    # sends.
    subscription_token_key_id: str = ""
    # Keys that are on their way out, as the JSON object {"kid": "secret"}. They verify but never
    # sign, so the two sides can be restarted one at a time: add the new key here on the inbox
    # first, switch the repository over, then drop the old one. It is a string rather than a dict
    # because the last step of a rotation is to empty it, and an empty value is not JSON - typed as
    # a dict, that would refuse to start rather than mean "none left".
    subscription_token_previous_secrets: str = ""
    # Who may issue a token, and which inbox it may be spent at. Both are optional, and an empty
    # one is not checked - but setting them is what stops a secret that is reused somewhere else
    # (or a token minted for another inbox) from being accepted here.
    subscription_token_issuer: str = ""
    subscription_token_audience: str = ""

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
