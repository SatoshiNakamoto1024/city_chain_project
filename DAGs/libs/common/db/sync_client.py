# D:\city_chain_project\network\DAGs\common\db\sync_client.py
"""PyMongo 同期クライアント (遅延接続＋コンテキストマネージャ)"""
from __future__ import annotations
from typing import Any
import os
from pymongo import MongoClient
from pymongo.collection import Collection

DEFAULT_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_DB  = os.getenv("DB_NAME", "federation_dag_db")


class SyncMongoClient:
    def __init__(self, *, uri: str | None = None, db_name: str | None = None) -> None:
        self._uri = uri or DEFAULT_URI
        self._db_name = db_name or DEFAULT_DB
        self._client: MongoClient | None = None   # lazy

    # -------- private helpers --------
    def _ensure(self) -> MongoClient:
        if self._client is None:
            self._client = MongoClient(self._uri, serverSelectionTimeoutMS=3000)
        return self._client

    # -------- public API -------------
    def collection(self, name: str) -> Collection[Any]:
        return self._ensure()[self._db_name][name]

    def insert_one(self, col: str, doc: dict[str, Any]):
        return self.collection(col).insert_one(doc).inserted_id

    def find_one(self, col: str, query: dict[str, Any]):
        return self.collection(col).find_one(query)

    # ... 必要に応じ more CRUD ...

    # -------- context support --------
    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # `with SyncMongoClient() as cli:` で使えるように
    def __enter__(self):  # noqa: D401
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D401
        self.close()
