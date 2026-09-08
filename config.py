from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

PAGE_LIMIT = 50

# The largest page a caller may ask for. Both listings took page_size with a lower bound but no
# upper one, so a single request could ask for every notification at once - the inbox is a public
# endpoint, so that is a cheap way to make it do a lot of work. Asking for more is refused (422)
# rather than quietly clamped, so a caller can tell the difference between "that is too many" and
# "that is all there is".
MAX_PAGE_SIZE = 500


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

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
