import os

from config import get_settings

from .adapters.base import BaseDBAdapter
from .adapters.mongo import MongoAdapter
from .adapters.postgres import PostgresAdapter

_ADAPTER: BaseDBAdapter | None = None


async def get_adapter() -> BaseDBAdapter:
    """Return the database adapter, building it on first use.

    The backend is chosen here and nowhere else:
        INBOX_PG_DSN set   -> PostgresAdapter
        MONGO_DB_URI set   -> MongoAdapter
    """
    global _ADAPTER  # pylint: disable=global-statement
    if _ADAPTER is None:
        dsn = os.environ.get("INBOX_PG_DSN")
        if dsn:
            _ADAPTER = PostgresAdapter(dsn)
        elif get_settings().mongo_db_uri:
            _ADAPTER = MongoAdapter(
                get_settings().mongo_db_uri, get_settings().mongo_db_name
            )
        else:
            raise RuntimeError(
                "no database configured: set INBOX_PG_DSN (PostgreSQL) "
                "or MONGO_DB_URI (MongoDB)"
            )
    return _ADAPTER
