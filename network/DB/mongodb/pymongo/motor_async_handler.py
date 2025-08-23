# \city_chain_project\network/db/mongodb/pymongo/motor_async_handler.py
# Async Motor wrapper with production-minded defaults:
# - Connection pool tuning via env
# - SecondaryPreferred reader
# - Optional write concern "majority" (env)
# - createdAt auto-fill
# - Retry insert
# - TTL(6 months) helper
# - Optional "content" transparent encrypt/decrypt (no-op by default)

import os
import math
import asyncio
import logging
from typing import Dict, Any, Optional, List

import motor.motor_asyncio
from motor.core import AgnosticDatabase, AgnosticCollection
from pymongo import ReadPreference, WriteConcern
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ========= 環境変数でプールやタイムアウトを調整 =========
def _env_u32(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

def _env_u64(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

MONGO_POOL_MAX      = _env_u32("MONGO_POOL_MAX", 200)         # maxPoolSize
MONGO_POOL_MIN      = _env_u32("MONGO_POOL_MIN", 20)          # minPoolSize
MONGO_POOL_IDLE_MS  = _env_u64("MONGO_POOL_IDLE_MS", 60_000)  # maxIdleTimeMS
MONGO_SST_MS        = _env_u32("MONGO_SST_MS", 5_000)         # serverSelectionTimeoutMS
MONGO_CONNECT_MS    = _env_u32("MONGO_CONNECT_MS", 5_000)     # connectTimeoutMS
MONGO_W_MAJORITY    = os.getenv("MONGO_W_MAJORITY", "0") == "1"  # write concern majority

# ========= 透過暗号（本番では CSFLE や AppLevel-Enc に置換可） =========
class _NoOpCE:
    def encrypt(self, v, *a, **k):
        return v
    def decrypt(self, v, *a, **k):
        return v

# 必要に応じて後で本物の CE を差し込めるようにしておく
CE = _NoOpCE()


class MotorDBHandler:
    """
    Async Motor wrapper aligned with Rust MongoDBAsyncHandler:
      - new() / new_with_read_preference()
      - insert/find/list/update/delete
      - insert_document_with_retry()
      - ensure_ttl_6months()
    """

    def __init__(self, client: motor.motor_asyncio.AsyncIOMotorClient, db: AgnosticDatabase):
        self.client = client
        self.db = db

    # ---------- factories ----------
    @classmethod
    async def new(cls, uri: str, dbname: str):
        """プライマリ指向（書き込み用）"""
        client = motor.motor_asyncio.AsyncIOMotorClient(
            uri,
            maxPoolSize=MONGO_POOL_MAX,
            minPoolSize=MONGO_POOL_MIN,
            maxIdleTimeMS=MONGO_POOL_IDLE_MS,
            serverSelectionTimeoutMS=MONGO_SST_MS,
            connectTimeoutMS=MONGO_CONNECT_MS,
            # ※ writeConcern は各操作（collection）側で設定する
        )
        return cls(client, client[dbname])

    @classmethod
    async def new_with_read_preference(cls, uri: str, dbname: str):
        """セカンダリ優先（読み取り用）"""
        client = motor.motor_asyncio.AsyncIOMotorClient(
            uri,
            maxPoolSize=MONGO_POOL_MAX,
            minPoolSize=MONGO_POOL_MIN,
            maxIdleTimeMS=MONGO_POOL_IDLE_MS,
            serverSelectionTimeoutMS=MONGO_SST_MS,
            connectTimeoutMS=MONGO_CONNECT_MS,
            readPreference="secondaryPreferred",  # Motor は文字列でも可
        )
        return cls(client, client[dbname])

    async def close_connection(self):
        self.client.close()

    # ---------- helpers ----------
    @staticmethod
    async def ensure_ttl_6months(collection: AgnosticCollection, field: str = "createdAt"):
        """
        6ヶ月 TTL を保証（存在すれば no-op）
        """
        try:
            await collection.create_index([(field, 1)], expireAfterSeconds=60 * 60 * 24 * 30 * 6, name="ttl_createdAt_6m")
        except Exception as e:
            logger.warning("ensure_ttl_6months failed on %s: %s", collection.name, e)

    def _coll(self, name: str) -> AgnosticCollection:
        c = self.db[name]
        if MONGO_W_MAJORITY:
            # 書き込みの耐障害性を優先する場合
            c = c.with_options(write_concern=WriteConcern(w="majority"))
        return c

    @staticmethod
    def _validate_document(d: Dict[str, Any]):
        for k, v in d.items():
            if isinstance(v, int) and not (-2**31 <= v < 2**31):
                raise ValueError(f"Int32 overflow: {k}")
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                raise ValueError(f"Invalid float: {k}")

    @staticmethod
    def _auto_created_at(d: Dict[str, Any]):
        if "createdAt" not in d:
            # PyMongo は Python の datetime を受け付けるが、ここでは簡単にサーバ時刻を使うため省略も可
            # 実運用は timezone-aware の datetime.utcnow() を推奨
            import datetime
            d["createdAt"] = datetime.datetime.utcnow()

    @staticmethod
    def _maybe_encrypt_content(d: Dict[str, Any]) -> Dict[str, Any]:
        if "content" in d:
            enc = dict(d)
            enc["content"] = CE.encrypt(enc["content"])
            return enc
        return d

    @staticmethod
    def _maybe_decrypt_content(d: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not d:
            return d
        if "content" in d:
            try:
                d = dict(d)
                d["content"] = CE.decrypt(d["content"])
            except Exception:
                pass
        return d

    # ---------- CRUD ----------
    async def insert_document(self, coll: str, doc: Dict[str, Any]) -> ObjectId:
        self._validate_document(doc)
        self._auto_created_at(doc)
        enc_doc = self._maybe_encrypt_content(doc)
        res = await self._coll(coll).insert_one(enc_doc)
        return res.inserted_id

    async def insert_document_with_retry(self, coll: str, doc: Dict[str, Any], max_retry: int = 5) -> ObjectId:
        last_err: Optional[Exception] = None
        for attempt in range(max_retry):
            try:
                return await self.insert_document(coll, dict(doc))  # clone
            except PyMongoError as e:
                last_err = e
                # バックオフ（50ms, 100ms, 150ms, ...）
                await asyncio.sleep(0.05 * (attempt + 1))
        assert last_err is not None
        raise last_err

    async def find_document(self, coll: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raw = await self._coll(coll).find_one(query)
        return self._maybe_decrypt_content(raw)

    async def list_documents(self, coll: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        async for d in self._coll(coll).find({}):
            out.append(self._maybe_decrypt_content(d) or d)
        return out

    async def update_document(self, coll: str, filter_: Dict[str, Any], fields: Dict[str, Any]) -> int:
        # $set に content があれば暗号化
        update_doc: Dict[str, Any] = {"$set": dict(fields)}
        if "content" in update_doc["$set"]:
            update_doc["$set"]["content"] = CE.encrypt(update_doc["$set"]["content"])
        res = await self._coll(coll).update_one(filter_, update_doc)
        return int(res.modified_count)

    async def delete_document(self, coll: str, filter_: Dict[str, Any]) -> int:
        res = await self._coll(coll).delete_one(filter_)
        return int(res.deleted_count)
