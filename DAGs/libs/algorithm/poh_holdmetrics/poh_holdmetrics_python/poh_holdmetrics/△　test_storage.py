# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_storage.py
# -*- coding: utf-8 -*-
"""
Storage‑layer integration test

* ローカル実 mongoDB (localhost:27017) へ実際に書き込む
* mongod が起動していない環境では xfail でスキップ
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import pytest
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError

from poh_holdmetrics.storage.mongodb import MongoStorage
from poh_holdmetrics.data_models import HoldEvent

# ---------------------------------------------------------------------------
#  環境変数 or デフォルト設定
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGODB_DB",  "pytest_tmp")

# ---------------------------------------------------------------------------
#  ヘルパー: mongod が立っているかを事前チェック
# ---------------------------------------------------------------------------
def _server_alive(uri: str) -> bool:
    try:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=1000)
        # 非同期だけど sync アクセスも可
        client.admin.command("ping")
        return True
    except Exception:
        return False
    finally:
        client.close()

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
    # 強制的に環境変数を上書きして MongoStorage に認識させる
    os.environ["MONGODB_URL"] = MONGO_URI
    os.environ["MONGODB_DB"]  = MONGO_DB

    store = MongoStorage()  # 接続文字列は上の env を読む
    await store.purge()     # まっさらな状態に

    # ── act ───────────────────────────────────────────────────
    now = datetime.now(tz=timezone.utc)
    ev  = HoldEvent("tk", "hd", now, now, 2.0)   # duration=0 → score=0
    await store.save_event(ev)

    stats = await store.get_stats()

    # ── assert ────────────────────────────────────────────────
    assert stats == []  # end == start なのでスコア0、match で除外されて空のはず

    # ── cleanup ───────────────────────────────────────────────
    await store.purge()
    await store.close()
