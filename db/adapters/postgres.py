import json
import os
from datetime import date, datetime

import asyncpg

from .base import BaseDBAdapter, UpdateResult

TABLE = "inbox_docs"


def encode(value):
    """Wrap datetimes as {"$date": "<ISO 8601>"} so JSONB round trips keep their type.

    Notification.updated is a datetime and app.py calls .isoformat() on it. Stored raw in
    JSONB it would come back as a string, so it is wrapped the way MongoDB Extended JSON
    does it.
    """
    if isinstance(value, (datetime, date)):
        return {"$date": value.isoformat()}
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    return value


def decode(value):
    """Unwrap {"$date": ...} back into a datetime."""
    if isinstance(value, dict):
        if set(value.keys()) == {"$date"}:
            try:
                return datetime.fromisoformat(value["$date"])
            except (TypeError, ValueError):
                return value["$date"]
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def build_where(db_filter, params):
    """Build the WHERE clause for a filter.

    params is the list of values bound to $1.., and the collection name always owns $1, so
    the placeholders produced here start at $2.
    """
    def eq(path, value):
        params.append(path)
        params.append(json.dumps(encode(value)))
        return f"(doc #> ${len(params) - 1}::text[]) = ${len(params)}::jsonb"

    clauses = []
    for key, value in (db_filter or {}).items():
        path = key.split(".")
        if isinstance(value, dict) and "$in" in value:
            ors = [eq(path, v) for v in value["$in"]]
            clauses.append("(" + (" OR ".join(ors) if ors else "false") + ")")
        else:
            clauses.append(eq(path, value))
    return " AND ".join(clauses) if clauses else "true"


def build_order_by(sort):
    """Build the ORDER BY clause, reaching inside the {"$date": ...} wrapper when present."""
    if not sort:
        return " ORDER BY seq ASC"
    key, direction = sort
    # The key is an in-app constant such as "updated"; sanitise it anyway.
    safe = "".join(ch for ch in str(key) if ch.isalnum() or ch in "_-")
    order = "DESC" if direction is not None and int(direction) < 0 else "ASC"
    return f" ORDER BY COALESCE(doc->'{safe}'->>'$date', doc->>'{safe}') {order}"


class PostgresAdapter(BaseDBAdapter):
    """The PostgreSQL backend, storing documents as JSONB.

    All collections share one table with a collection column. There are only five of them and
    the queries are exact, dotted or $in matches, so this is simpler and faster than a table
    per collection.
    """

    def __init__(self, dsn: str | None = None):
        self._dsn = dsn or os.environ.get("INBOX_PG_DSN")
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            if not self._dsn:
                raise RuntimeError("INBOX_PG_DSN is not set")
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)
            async with self._pool.acquire() as con:
                await con.execute(
                    f"CREATE TABLE IF NOT EXISTS {TABLE} ("
                    "  seq        bigserial PRIMARY KEY,"
                    "  collection text  NOT NULL,"
                    "  doc        jsonb NOT NULL)"
                )
                await con.execute(
                    f"CREATE INDEX IF NOT EXISTS {TABLE}_collection_idx "
                    f"ON {TABLE} (collection)"
                )
                await con.execute(
                    f"CREATE INDEX IF NOT EXISTS {TABLE}_doc_idx "
                    f"ON {TABLE} USING gin (doc jsonb_path_ops)"
                )
        return self._pool

    async def insert_one(self, collection_name, data):
        pool = await self._get_pool()
        async with pool.acquire() as con:
            await con.execute(
                f"INSERT INTO {TABLE} (collection, doc) VALUES ($1, $2::jsonb)",
                collection_name, json.dumps(encode(data)),
            )

    async def find_one(self, collection_name, db_filter):
        rows = await self.find(collection_name, db_filter, limit=1)
        return rows[0] if rows else None

    async def find(self, collection_name, db_filter, sort=None, skip=0, limit=0):
        params = [collection_name]
        where = build_where(db_filter, params)
        sql = (
            f"SELECT doc FROM {TABLE} WHERE collection = $1 AND {where}"
            + build_order_by(sort)
        )
        if limit:
            params.append(int(limit))
            sql += f" LIMIT ${len(params)}"
        if skip:
            params.append(int(skip))
            sql += f" OFFSET ${len(params)}"
        pool = await self._get_pool()
        async with pool.acquire() as con:
            rows = await con.fetch(sql, *params)
        return [decode(json.loads(r["doc"])) for r in rows]

    async def update_one(self, collection_name, db_filter, update_data, upsert=False):
        params = [collection_name]
        where = build_where(db_filter, params)
        params.append(json.dumps(encode(update_data)))
        # Update only the oldest matching row, as MongoDB's update_one does.
        sql = (
            f"UPDATE {TABLE} SET doc = doc || ${len(params)}::jsonb WHERE seq = "
            f"(SELECT seq FROM {TABLE} WHERE collection = $1 AND {where} "
            "ORDER BY seq ASC LIMIT 1)"
        )
        pool = await self._get_pool()
        async with pool.acquire() as con:
            status = await con.execute(sql, *params)
            matched = int(status.rsplit(" ", 1)[-1]) if status.startswith("UPDATE") else 0
            if matched == 0 and upsert:
                # Create it including the filter keys, matching MongoDB's upsert.
                doc = {
                    k: v for k, v in (db_filter or {}).items() if not isinstance(v, dict)
                }
                doc.update(update_data)
                await con.execute(
                    f"INSERT INTO {TABLE} (collection, doc) VALUES ($1, $2::jsonb)",
                    collection_name, json.dumps(encode(doc)),
                )
                return UpdateResult(0, inserted=True)
        return UpdateResult(matched)

    async def delete_one(self, collection_name, db_filter):
        params = [collection_name]
        where = build_where(db_filter, params)
        sql = (
            f"DELETE FROM {TABLE} WHERE seq = "
            f"(SELECT seq FROM {TABLE} WHERE collection = $1 AND {where} "
            "ORDER BY seq ASC LIMIT 1)"
        )
        pool = await self._get_pool()
        async with pool.acquire() as con:
            status = await con.execute(sql, *params)
        return int(status.rsplit(" ", 1)[-1]) if status.startswith("DELETE") else 0

    async def delete_many(self, collection_name, db_filter):
        params = [collection_name]
        where = build_where(db_filter, params)
        pool = await self._get_pool()
        async with pool.acquire() as con:
            status = await con.execute(
                f"DELETE FROM {TABLE} WHERE collection = $1 AND {where}", *params
            )
        return int(status.rsplit(" ", 1)[-1]) if status.startswith("DELETE") else 0

    async def count(self, collection_name, db_filter=None):
        params = [collection_name]
        where = build_where(db_filter, params)
        pool = await self._get_pool()
        async with pool.acquire() as con:
            row = await con.fetchrow(
                f"SELECT count(*) AS n FROM {TABLE} WHERE collection = $1 AND {where}",
                *params,
            )
        return int(row["n"])
