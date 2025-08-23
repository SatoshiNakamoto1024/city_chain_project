# D:\city_chain_project\network\sending_DAGs\python_sending\common\db.py
"""
common.db
=========
同期／非同期の MongoDB クライアントを共通提供する薄いラッパー。

* `get_sync_client`   : コンテキストマネージャで同期 MongoClient
* `get_async_client`  : motor.asyncio 版 (存在しなければ ImportError を投げる)
"""

from __future__ import annotations

import contextlib
import os
from typing import Any, AsyncIterator

# ───────────────────────────────
# デフォルト設定（環境変数で上書き可）
# ───────────────────────────────
DEFAULT_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_DB = os.getenv("DB_NAME", "federation_dag_db")


# ───────────────────────────────
# 同期版ラッパー
# ───────────────────────────────
class _SyncClientWrapper:
    """
    with _SyncClientWrapper(...) as cli:
        cli.insert_one("col", {...})
    """

    def __init__(self, uri: str, db_name: str):
        from pymongo import MongoClient  # ※ローカル import でテストが軽くなる
        self._client = MongoClient(uri)
        self._db = self._client[db_name]

    # ----- CRUD 最低限だけ実装 -----
    def insert_one(self, col: str, doc: dict[str, Any]):
        return self._db[col].insert_one(doc).inserted_id

    def find_one(self, col: str, query: dict[str, Any] | None = None):
        return self._db[col].find_one(query or {})

    # ----- context-manager -----
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # 明示的 close
        self._client.close()


def get_sync_client(
    *,
    uri: str = DEFAULT_URI,
    db_name: str = DEFAULT_DB
) -> contextlib.AbstractContextManager[_SyncClientWrapper]:
    """
    Example
    -------
    ```python
    with get_sync_client() as cli:
        cli.insert_one("mycol", {"x": 1})
    ```
    """
    return _SyncClientWrapper(uri, db_name)


# ───────────────────────────────
# 非同期版ラッパー (Motor)
# ───────────────────────────────
class _AsyncClientWrapper:
    """
    async with _AsyncClientWrapper(...) as cli:
        await cli.insert_one("col", {...})
    """

    def __init__(self, uri: str, db_name: str):
        try:
            from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError("motor がインストールされていません") from e
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[db_name]

    # async CRUD
    async def insert_one(self, col: str, doc: dict[str, Any]):
        res = await self._db[col].insert_one(doc)
        return res.inserted_id

    async def find_one(self, col: str, query: dict[str, Any] | None = None):
        return await self._db[col].find_one(query or {})

    # async context-manager
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._client.close()


def get_async_client(
    *,
    uri: str = DEFAULT_URI,
    db_name: str = DEFAULT_DB
) -> AsyncIterator[_AsyncClientWrapper]:
    """
    Example
    -------
    ```python
    async with get_async_client() as cli:
        await cli.insert_one("mycol", {"x": 1})
    ```
    """
    return _AsyncClientWrapper(uri, db_name)  # これは async context-manager


# ───────────────────────────────
# __all__
# ───────────────────────────────
__all__ = [
    "get_async_client",
    "get_sync_client",
]
