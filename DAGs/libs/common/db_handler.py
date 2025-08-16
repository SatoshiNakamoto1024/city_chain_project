# D:\city_chain_project\network\sending_DAGs\python_sending\common\db_handler.py
# D:\city_chain_project\network\sending_DAG\python_sending\common\db_handler.py
"""
common.db_handler
=================
*同期* パス専用の軽量ユーティリティ。

変更点
------
1. 遅延接続 + context-manager で `ResourceWarning` を解消
2. `save_completed_tx_to_mongo()` に `_db` キーワードを追加
   → テストや呼び出し側で好きな `pymongo.database.Database` を注入できる
3. `uri` / `db_name` もキーワードで上書き可能
4. 非同期が欲しい場合は `common.db.get_async_client()` を直接呼ぶ
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.db import get_sync_client  # 同期クライアントファクトリ

# ─────────────────────────────
# Logger
# ─────────────────────────────
logger = logging.getLogger("common.db_handler")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# ─────────────────────────────
# デフォルト接続情報（環境変数で上書き可）
# ─────────────────────────────
DEFAULT_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_DB  = os.getenv("DB_NAME", "federation_dag_db")

# ─────────────────────────────
# Public API
# ─────────────────────────────
def save_completed_tx_to_mongo(
    record: dict[str, Any],
    collection_name: str = "completed_transactions",
    *,
    _db: "Optional[object]" = None,          # ← ★ ここが新規
    uri: str | None = None,
    db_name: str | None = None,
):
    """
    完了トランザクション / バッチを 1 件だけ同期書き込み。

    Parameters
    ----------
    record : dict
        保存するドキュメント
    collection_name : str
        コレクション名（既定 `"completed_transactions"`）
    _db : pymongo.database.Database, optional
        **テストや DI 用**―既に取得済み DB インスタンスを直接渡したい場合に使用
    uri / db_name : str, optional
        MongoDB 接続先を個別に指定したい場合に指定。
        `_db` が与えられている場合は無視される。
    """
    if _db is not None:
        collection = _db[collection_name]
        res = collection.insert_one(record)
        logger.info(
            "[DBHandler] inserted %s (col=%s, injected-db)", res.inserted_id, collection_name
        )
        return res.inserted_id

    _uri     = uri or DEFAULT_URI
    _db_name = db_name or DEFAULT_DB

    try:
        with get_sync_client(uri=_uri) as client:
            db  = client[_db_name]
            res = db[collection_name].insert_one(record)
            logger.info(
                "[DBHandler] inserted %s (col=%s, db=%s)", res.inserted_id, collection_name, _db_name
            )
            return res.inserted_id
    except Exception as exc:  # pragma: no cover
        logger.error("[DBHandler] insert failed: %s", exc, exc_info=True)
        return None


__all__ = ["save_completed_tx_to_mongo"]
