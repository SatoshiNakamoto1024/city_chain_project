# D:\city_chain_project\network\DAGs\common\db\async_client.py
"""Motor 非同期クライアント (遅延接続＋async with)"""
from __future__ import annotations
from typing import Any
import os
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticCollection

DEFAULT_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_DB = os.getenv("DB_NAME", "federation_dag_db")


class AsyncMongoClient:
    """`async with AsyncMongoClient.create() as cli:` で利用"""

    def __init__(self, client: AsyncIOMotorClient, db_name: str) -> None:
        self._client = client
        self._db = client[db_name]

    # ---------- factory ----------
    @classmethod
    async def create(cls, *, uri: str | None = None, db_name: str | None = None
                     ) -> "AsyncMongoClient":
        client = AsyncIOMotorClient(uri or DEFAULT_URI, serverSelectionTimeoutMS=3000)
        # 1 度 ping して接続確認
        await client.admin.command("ping")
        return cls(client, db_name or DEFAULT_DB)

    # ---------- CRUD --------------
    def collection(self, name: str) -> AgnosticCollection[Any]:
        return self._db[name]

    async def insert_one(self, col: str, doc: dict[str, Any]):
        res = await self.collection(col).insert_one(doc)
        return res.inserted_id

    async def find_one(self, col: str, query: dict[str, Any]):
        return await self.collection(col).find_one(query)

    # ... more async CRUD ...

    # ---------- context ------------
    async def aclose(self) -> None:
        self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
