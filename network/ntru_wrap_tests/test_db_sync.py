# network/tests/test_db_sync.py
from __future__ import annotations
import pytest
import common as C  # ← lazy import 再エクスポート済み
from bson import ObjectId

@pytest.mark.parametrize("collection", ["completed_transactions"])
def test_sync_insert(mongo_uri: str, mongo_dbname: str, collection: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    common.db_handler が **実際に insert しているか** を検証。  
    mongomock:// の場合でも同じコードで OK。
    """
    # --- ① Setup: DB をモック or 実 DB に差し替え ---
    if mongo_uri.startswith("mongomock://"):
        import mongomock  # type: ignore
        client = mongomock.MongoClient()
        monkeypatch.setattr(C.db_handler, "get_sync_client", lambda **kw: C.db.sync_client.SyncMongoClient(client, mongo_dbname))  # type: ignore

    # --- ② 実行 ---
    oid = C.db_handler.save_completed_tx_to_mongo(
        {"foo": "bar", "n": 42}, collection_name=collection, uri=mongo_uri, db_name=mongo_dbname
    )

    # --- ③ 検証 ---
    assert isinstance(oid, ObjectId)
    with C.db.get_sync_client(uri=mongo_uri, db_name=mongo_dbname) as cli:  # type: ignore
        cnt = cli.db[collection].count_documents({"_id": oid})            # type: ignore[attr-defined]
    assert cnt == 1
