# D:\city_chain_project\network\sending_DAGs\python_sending\common\db_handler.py
"""
common.db_handler
=================
*同期専用* で “単発 insert だけ出来れば OK” という軽量ユーティリティ。

- **遅延接続 + with-close** に変更し ResourceWarning を解消
- 接続情報は環境変数か呼び出し側で上書き
- 非同期経路が必要な場合は `common.db.get_async_client()` を直接使う
"""
from __future__ import annotations
import logging
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Any
from common.db import get_sync_client   # ← 新ファクトリ

# ───────────────────────────────
# ロガー
# ───────────────────────────────
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ───────────────────────────────
# 環境変数 (デフォルト値)
# ───────────────────────────────
DEFAULT_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_DB  = os.getenv("DB_NAME", "federation_dag_db")

# ───────────────────────────────
# Public API
# ───────────────────────────────
def save_completed_tx_to_mongo(
    record: dict[str, Any],
    collection_name: str = "completed_transactions",
    *,
    uri: str | None = None,
    db_name: str | None = None,
):
    """
    受信完了したトランザクション／バッチを **同期クライアント** で 1 件保存。

    Parameters
    ----------
    record : dict
        保存するドキュメント
    collection_name : str
        コレクション名（デフォルト `"completed_transactions"`)
    uri / db_name : Optional[str]
        MongoDB 接続先を個別指定したい時に渡す。
        省略時は環境変数 `MONGODB_URI` / `DB_NAME`
    """
    _uri = uri or DEFAULT_URI
    _db  = db_name or DEFAULT_DB

    try:
        with get_sync_client(uri=_uri, db_name=_db) as cli:
            oid = cli.insert_one(collection_name, record)
            logger.info(
                "[DBHandler] inserted %s (col=%s, db=%s)",
                oid, collection_name, _db
            )
            return oid
    except Exception as exc:  # pragma: no cover
        logger.error("[DBHandler] insert failed: %s", exc, exc_info=True)
        return None


__all__ = ["save_completed_tx_to_mongo"]
