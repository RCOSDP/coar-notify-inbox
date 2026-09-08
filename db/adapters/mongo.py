from motor.motor_asyncio import AsyncIOMotorClient

from .base import BaseDBAdapter, UpdateResult


class MongoAdapter(BaseDBAdapter):

    _NO_ID = {"_id": 0}

    def __init__(self, uri: str, db_name: str):
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[db_name]

    def _collection(self, collection_name):
        return self._db[collection_name]

    async def insert_one(self, collection_name, data):
        await self._collection(collection_name).insert_one(dict(data))

    async def find_one(self, collection_name, db_filter):
        return await self._collection(collection_name).find_one(db_filter or {}, self._NO_ID)

    async def find(self, collection_name, db_filter, sort=None, skip=0, limit=0):
        cursor = self._collection(collection_name).find(db_filter or {}, self._NO_ID)
        if sort:
            cursor = cursor.sort(sort[0], sort[1])
        if skip:
            cursor = cursor.skip(int(skip))
        if limit:
            cursor = cursor.limit(int(limit))
        return await cursor.to_list(length=int(limit) if limit else 1000)

    async def update_one(self, collection_name, db_filter, update_data, upsert=False):
        result = await self._collection(collection_name).update_one(
            db_filter or {}, {"$set": dict(update_data)}, upsert=upsert
        )
        return UpdateResult(result.matched_count, inserted=result.upserted_id is not None)

    async def delete_one(self, collection_name, db_filter):
        result = await self._collection(collection_name).delete_one(db_filter or {})
        return result.deleted_count

    async def delete_many(self, collection_name, db_filter):
        result = await self._collection(collection_name).delete_many(db_filter or {})
        return result.deleted_count

    async def count(self, collection_name, db_filter=None):
        return await self._collection(collection_name).count_documents(db_filter or {})
