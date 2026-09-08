from abc import ABC, abstractmethod


class UpdateResult:
    """The outcome of an update.

    Callers need both facts: update_notification_state raises when nothing matched, while
    routers/subscriptions.py answers 201 on an insert and 200 on an update of an existing
    document.
    """

    __slots__ = ("matched", "inserted")

    def __init__(self, matched: int, inserted: bool = False):
        self.matched = matched
        self.inserted = inserted

    def __bool__(self):
        return bool(self.matched or self.inserted)

    def __repr__(self):
        return f"UpdateResult(matched={self.matched}, inserted={self.inserted})"


class BaseDBAdapter(ABC):
    """A backend-independent interface to the inbox's storage.

    Filters support exactly two forms, which is all the application uses:

        {"id": "..."}            exact match; a dotted key such as "target.id" addresses a
                                 nested value
        {"k": {"$in": [...]}}    matches any of the values
    """

    @abstractmethod
    async def insert_one(self, collection_name: str, data: dict) -> None:
        """Insert one document."""

    @abstractmethod
    async def find_one(self, collection_name: str, db_filter: dict) -> dict | None:
        """Return the first document matching the filter, or None."""

    @abstractmethod
    async def find(
        self,
        collection_name: str,
        db_filter: dict,
        sort: tuple[str, int] | None = None,
        skip: int = 0,
        limit: int = 0,
    ) -> list[dict]:
        """Return matching documents, ordered and paged.

        sort is (key, 1) for ascending or (key, -1) for descending.
        """

    @abstractmethod
    async def update_one(
        self,
        collection_name: str,
        db_filter: dict,
        update_data: dict,
        upsert: bool = False,
    ) -> UpdateResult:
        """Update the fields of one matching document.

        With upsert=True the document is created when no match exists.
        """

    @abstractmethod
    async def delete_one(self, collection_name: str, db_filter: dict) -> int:
        """Delete one matching document and return how many were deleted."""

    @abstractmethod
    async def delete_many(self, collection_name: str, db_filter: dict) -> int:
        """Delete every matching document and return how many were deleted."""

    @abstractmethod
    async def count(self, collection_name: str, db_filter: dict | None = None) -> int:
        """Return how many documents match the filter."""
