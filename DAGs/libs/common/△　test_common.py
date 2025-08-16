# D:\city_chain_project\network\sending_DAGs\python_sending\common\test_common.py
"""
共通ユーティリティの煙テスト
---------------------------------
MongoDB がない環境でも落ちないよう `save_completed_tx_to_mongo`
は `mongomock` がある場合だけ実際に書き込みを行う。
"""

import os
import json
import pytest
from types import SimpleNamespace as NS

import common as C


def test_dynamic_batch_interval():
    # pending が 0 → interval が伸びる
    i1 = C.config.get_dynamic_batch_interval(0)
    i2 = C.config.get_dynamic_batch_interval(0)
    assert i2 >= i1

    # pending が多い → interval が最小に張り付く
    i3 = C.config.get_dynamic_batch_interval(C.config.MAX_TX_PER_BATCH + 1)
    assert i3 == C.config.MIN_BATCH_INTERVAL


@pytest.mark.skipif("MONGODB_URI" not in os.environ, reason="MongoDB 未設定")
def test_save_tx(monkeypatch):
    # mongomock を使う
    import mongomock
    client = mongomock.MongoClient()
    monkeypatch.setattr(C.db_handler, "client", client)
    monkeypatch.setattr(C.db_handler, "db", client["unit_test"])

    oid = C.db_handler.save_completed_tx_to_mongo({"foo": "bar"})
    assert oid is not None
    assert C.db_handler.db.completed_transactions.count_documents({}) == 1


def test_distributed_storage(tmp_path, monkeypatch):
    # ストレージ先を一時ディレクトリに
    monkeypatch.chdir(tmp_path)
    ok = C.distributed_storage_system.store_transaction_frag(
        "nodeX", "tx1", "sh0", {"a": 1}
    )
    assert ok
    data = C.distributed_storage_system.restore_transaction_frag("nodeX", "tx1", "sh0")
    assert data["a"] == 1
