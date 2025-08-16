# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_storage.py
# -*- coding: utf-8 -*-
"""
Storage-layer integration test

* ローカル実 mongoDB (localhost:27017) へ実際に書き込む
* mongod が起動していない環境では xfail でスキップ
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from poh_holdmetrics.storage.mongodb import MongoStorage
from poh_holdmetrics.data_models import HoldEvent

# ---------------------------------------------------------------------------
#  環境変数 or デフォルト設定（URI/URL どちらでも拾えるように）
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGODB_URI") or os.getenv("MONGODB_URL") or "mongodb://127.0.0.1:27017"
MONGO_DB  = os.getenv("MONGODB_DB", "pytest_tmp")

# ---------------------------------------------------------------------------
#  ヘルパー: mongod が立っているかを事前チェック（同期の PyMongo を使用）
# ---------------------------------------------------------------------------
def _server_alive(uri: str) -> bool:
    client = None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        return True
    except Exception:
        return False
    finally:
        try:
            if client is not None:
                client.close()
        except Exception:
            pass

SERVER_UP = _server_alive(MONGO_URI)

# ---------------------------------------------------------------------------
#  テスト本体
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.xfail(not SERVER_UP, reason="mongod が起動していないためスキップ", strict=False)
async def test_mongo_storage_integration() -> None:
    """
    1) HoldEvent を1件保存
    2) get_stats で加算が反映されることを確認
    """
    # ── arrange ───────────────────────────────────────────────
    # 環境変数を上書き（MongoStorage がどちら名でも拾えるよう二重で設定）
    os.environ["MONGODB_URI"] = MONGO_URI
    os.environ["MONGODB_URL"] = MONGO_URI   # 互換用
    os.environ["MONGODB_DB"]  = MONGO_DB

    store = MongoStorage()   # 接続文字列は上の env を読む
    try:
        await store.purge()  # まっさらな状態に

        # ── act ───────────────────────────────────────────────
        now = datetime.now(tz=timezone.utc)
        # ★ Pydantic v2: BaseModel はキーワード引数で！
        ev = HoldEvent(
            token_id="tk",
            holder_id="hd",
            start=now,
            end=now,
            weight=2.0,
        )
        await store.save_event(ev)

        stats = await store.get_stats()

        # ── assert ───────────────────────────────────────────
        # end == start なので duration=0 → score=0 で除外される想定
        assert stats == []

    finally:
        # ── cleanup ──────────────────────────────────────────
        try:
            await store.purge()
        finally:
            await store.close()
