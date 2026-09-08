from abc import ABC, abstractmethod
from typing import Union


class UpdateResult:

    __slots__ = ("matched", "inserted")

    def __init__(self, matched: int, inserted: bool = False):
        self.matched = matched
        self.inserted = inserted

    def __bool__(self):
        return bool(self.matched or self.inserted)

    def __repr__(self):
        return f"UpdateResult(matched={self.matched}, inserted={self.inserted})"


class BaseDBAdapter(ABC):
    """Backend independent access to the stored documents.

    Filters accept an exact match, a dotted key for a nested value, and {"$in": [...]}.
    """

    @abstractmethod
    async def insert_one(self, collection_name: str, data: dict) -> None:
        pass

    @abstractmethod
    async def find_one(self, collection_name: str, db_filter: dict) -> Union[dict, None]:
        pass

    @abstractmethod
    async def find(self, collection_name: str, db_filter: dict,
                   sort: Union[tuple, None] = None,
                   skip: int = 0, limit: int = 0) -> list[dict]:
        pass

    @abstractmethod
    async def update_one(self, collection_name: str, db_filter: dict,
                         update_data: dict, upsert: bool = False) -> UpdateResult:
        pass

    @abstractmethod
    async def delete_one(self, collection_name: str, db_filter: dict) -> int:
        pass

    @abstractmethod
    async def delete_many(self, collection_name: str, db_filter: dict) -> int:
        pass

    @abstractmethod
    async def count(self, collection_name: str, db_filter: Union[dict, None] = None) -> int:
        pass
