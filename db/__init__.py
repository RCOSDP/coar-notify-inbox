import os

from config import get_settings

from .adapters.base import BaseDBAdapter
from .adapters.mongo import MongoAdapter
from .adapters.postgres import PostgresAdapter

MONGO_DB_NAME = "notification_store"

_ADAPTER = None


async def get_adapter() -> BaseDBAdapter:
    """Return the adapter for the configured backend."""
    global _ADAPTER  # pylint: disable=global-statement
    if _ADAPTER is None:
        dsn = os.environ.get("INBOX_PG_DSN")
        if dsn:
            _ADAPTER = PostgresAdapter(dsn)
        elif get_settings().mongo_db_uri:
            _ADAPTER = MongoAdapter(get_settings().mongo_db_uri, MONGO_DB_NAME)
        else:
            raise RuntimeError("no database configured: set INBOX_PG_DSN or MONGO_DB_URI")
    return _ADAPTER
