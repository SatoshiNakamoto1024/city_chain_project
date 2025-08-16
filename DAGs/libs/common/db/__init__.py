# D:\city_chain_project\network\DAGs\common\db\__init__.py
"""
common.db
~~~~~~~~~
`get_sync_client()` / `get_async_client()` ファクトリを提供し、
使い終わったら *必ず* `close()` / `await aclose()` を呼ぶ。

例::

    from common.db import get_sync_client, get_async_client

    with get_sync_client() as cli:
        oid = cli.insert_one("tx", {"foo": 1})

    async with get_async_client() as acli:
        await acli.insert_one("tx", {"bar": 2})
"""
from __future__ import annotations
from contextlib import contextmanager, asynccontextmanager
from typing import Iterator, AsyncIterator
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.sync_client import SyncMongoClient
from db.async_client import AsyncMongoClient

# ─────────── Sync───────────
@contextmanager
def get_sync_client(uri: str | None = None, db_name: str | None = None
                    ) -> Iterator[SyncMongoClient]:
    cli = SyncMongoClient(uri=uri, db_name=db_name)
    try:
        yield cli
    finally:
        cli.close()

# ─────────── Async──────────
@asynccontextmanager
async def get_async_client(uri: str | None = None, db_name: str | None = None
                           ) -> AsyncIterator[AsyncMongoClient]:
    cli = await AsyncMongoClient.create(uri=uri, db_name=db_name)
    try:
        yield cli
    finally:
        await cli.aclose()

__all__ = [
    "SyncMongoClient",
    "AsyncMongoClient",
    "get_sync_client",
    "get_async_client",
]
