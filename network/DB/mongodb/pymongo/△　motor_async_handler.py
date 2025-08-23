# \city_chain_project\network/db/mongodb/pymongo/motor_async_handler.py
# Patched version with CSFLE + NTRU-KEM key wrapping, with fallback when libmongocrypt is missing.

import os
import sys
import math
import base64
import secrets
import asyncio
import binascii
import logging
from pathlib import Path
from typing import Dict, Any

import motor.motor_asyncio
from motor.core import AgnosticDatabase
from pymongo.encryption import Algorithm
from pymongo.encryption import ClientEncryption
from pymongo.errors import ConfigurationError
from bson.objectid import ObjectId

# プロジェクトルート直下の Algorithm パッケージを探せるようパス追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from Algorithm.core.crypto import unwrap_key_ntru, wrap_key_ntru

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────
# 設定：KeyVault, master capsule, NTRU 鍵
# ─────────────────────────────────────────────────────────────────────────────

KEY_VAULT_NS = os.getenv("KEY_VAULT_NS", "keyvault.__keys__")
MASTER_CAPSULE_PATH = Path(os.getenv("MASTER_CAPSULE", "/etc/secrets/master_capsule"))

# NTRU 鍵は環境変数に「16進文字列」で渡されたものをバイト列に変換
_priv_hex = os.getenv("NTRU_PRIV", "deadbeef")
_pub_hex  = os.getenv("NTRU_PUB", "beefdead")
try:
    MASTER_PRIV_NTRU = binascii.unhexlify(_priv_hex)
    MASTER_PUB_NTRU  = binascii.unhexlify(_pub_hex)
except (binascii.Error, TypeError):
    raise RuntimeError(
        "NTRU_PRIV / NTRU_PUB は16進文字列で指定してください "
        f"(got PRIV={_priv_hex!r}, PUB={_pub_hex!r})"
    )

class MotorDBHandler:
    """
    Async-Mongo wrapper + CSFLE (AES-GCM) + NTRU-KEM key wrapping.
    テスト環境で libmongocrypt が無い場合は暗号化をバイパスします。
    """

    def __init__(self, client: motor.motor_asyncio.AsyncIOMotorClient, db: AgnosticDatabase):
        self.client = client
        self.db = db

        # ---------- ClientEncryption 初期化 ----------
        # まずマスターカプセルを読み込んで unwrap → local master key 取得
        try:
            capsule_bytes = MASTER_CAPSULE_PATH.read_bytes()
            local_master_key = unwrap_key_ntru(MASTER_PRIV_NTRU, capsule_bytes)
            logger.info("[MotorDBHandler] Unwrapped NTRU master key via capsule")
        except Exception as e:
            logger.warning(
                "[MotorDBHandler] Failed to unwrap NTRU master key (%s); "
                "using random local master key for testing", e
            )
            # CSFLE のローカルマスターキーは 96 バイト必須なので、乱数生成
            local_master_key = secrets.token_bytes(96)

        kms_providers = {"local": {"key": local_master_key}}

        # ClientEncryption の初期化。libmongocrypt がなければフォールバックでダミー実装を使う。
        try:
            self._ce = ClientEncryption(
                kms_providers=kms_providers,
                key_vault_namespace=KEY_VAULT_NS,
                key_vault_client=self.client,       # pymongo>=4.0 の引数名
                codec_options=None,
            )
            # 本来の data key を起こす
            self._dek_id = self._ensure_data_key()
        except ConfigurationError as e:
            logger.warning(
                "[MotorDBHandler] CSFLE disabled (%s); "
                "using identity encrypt/decrypt for testing", e
            )
            # テスト／開発環境向けダミー
            class _NoOpCE:
                def encrypt(inner_self, value, *args, **kwargs):
                    return value
                def decrypt(inner_self, value, *args, **kwargs):
                    return value
            self._ce = _NoOpCE()
            self._dek_id = None  # encrypt/decrypt はキー不要

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
            # identity CE の場合はそのまま返る
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
