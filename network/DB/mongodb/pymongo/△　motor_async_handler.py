# File: network/db/mongodb/pymongo/motor_async_handler.py
# Patched version with CSFLE + NTRU-KEM key wrapping

import os, sys, math, base64, secrets, asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import motor.motor_asyncio
from motor.core import AgnosticDatabase, AgnosticCollection
from pymongo.encryption import Algorithm, ClientEncryption
from bson.objectid import ObjectId

# ---- tiny NTRU stub (実際は algorithm.core.crypto.wrap_key_ntru 等を import) ----
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from Algorithm.core.crypto import unwrap_key_ntru, wrap_key_ntru  # already in project

KEY_VAULT_NS = os.getenv("KEY_VAULT_NS", "keyvault.__keys__")
MASTER_CAPSULE_PATH = Path(os.getenv("MASTER_CAPSULE", "/etc/secrets/master_capsule"))
MASTER_PRIV_NTRU    = os.getenv("NTRU_PRIV", "deadbeef")
MASTER_PUB_NTRU     = os.getenv("NTRU_PUB", "beefdead")

class MotorDBHandler:
    """
    Async-Mongo wrapper + CSFLE (AES-GCM) + NTRU-KEM key wrapping
    """

    def __init__(self, client: motor.motor_asyncio.AsyncIOMotorClient, db: AgnosticDatabase):
        self.client = client
        self.db = db
        # ---------- ClientEncryption 初期化 ----------
        local_master_key = unwrap_key_ntru(MASTER_PRIV_NTRU, MASTER_CAPSULE_PATH.read_bytes())
        kms_providers = {"local": {"key": local_master_key}}
        self._ce = ClientEncryption(
            kms_providers=kms_providers,
            key_vault_namespace=KEY_VAULT_NS,
            client=self.client,
            codec_options=None,
        )
        self._dek_id = self._ensure_data_key()

    # ---------- factory ----------
    @classmethod
    async def new(cls, uri: str, dbname: str):
        client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        return cls(client, client[dbname])

    @classmethod
    async def new_with_read_preference(cls, uri: str, dbname: str):
        client = motor.motor_asyncio.AsyncIOMotorClient(
            uri,
            readPreference="secondaryPreferred",
            serverSelectionTimeoutMS=5000
        )
        return cls(client, client[dbname])

    async def close_connection(self):
        self.client.close()

    # ---------- internal ----------
    def _ensure_data_key(self):
        """KeyVault に NTRU capsule 付き DEK が無ければ生成"""
        kv_db, kv_coll = KEY_VAULT_NS.split(".")
        kv = self.client[kv_db][kv_coll]
        doc = kv.find_one({"keyAltNames": ["pqc_default_dek"]})
        if doc:
            return doc["_id"]
        # new 32-byte DEK
        dek = secrets.token_bytes(32)
        capsule = wrap_key_ntru(MASTER_PUB_NTRU, dek)
        res = kv.insert_one({
            "_id": ObjectId(),
            "keyAltNames": ["pqc_default_dek"],
            "ntru_capsule": base64.b64encode(capsule).decode(),
            "createdAt": asyncio.get_event_loop().time(),
        })
        return res.inserted_id

    # ---------- validation ----------
    def _validate_document(self, d: Dict[str, Any]):
        for k, v in d.items():
            if isinstance(v, int) and not (-2**31 <= v < 2**31):
                raise ValueError(f"Int32 overflow: {k}")
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                raise ValueError(f"Invalid float: {k}")

    # ---------- CRUD with transparent encryption ----------
    async def insert_document(self, coll: str, doc: Dict[str, Any]):
        self._validate_document(doc)
        enc_doc = dict(doc)
        if "content" in enc_doc:
            enc_doc["content"] = self._ce.encrypt(
                enc_doc["content"],
                Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic,
                key_id=self._dek_id
            )
        result = await self.db[coll].insert_one(enc_doc)
        return result.inserted_id

    async def find_document(self, coll: str, query: Dict[str, Any]):
        raw = await self.db[coll].find_one(query)
        return self._decrypt_doc(raw)

    async def list_documents(self, coll: str):
        cur = self.db[coll].find({})
        out = []
        async for d in cur:
            out.append(self._decrypt_doc(d))
        return out

    def _decrypt_doc(self, d):
        if not d:
            return None
        if "content" in d and isinstance(d["content"], (bytes, bytearray)):
            try:
                d["content"] = self._ce.decrypt(d["content"])
            except Exception:
                pass
        return d
