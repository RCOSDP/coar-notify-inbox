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
    icon:str = ""

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
