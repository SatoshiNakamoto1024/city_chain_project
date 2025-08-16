# D:\city_chain_project\network\sending_DAGs\python_sending\common\test_common.py
"""
common パッケージのスモークテスト
────────────────────────────────────────────
MongoDB が無い環境でも落ちないように `mongomock` を使うだけで、
本物の Mongo は要りません。
"""

from __future__ import annotations

import os
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any

import pytest

import common as C


# ════════════════════════════════════════════════════════
# 1) dynamic batch-interval
# ════════════════════════════════════════════════════════
def test_dynamic_batch_interval() -> None:
    i1 = C.config.get_dynamic_batch_interval(0)
    i2 = C.config.get_dynamic_batch_interval(0)
    assert i2 >= i1  # 閑散時は伸びる

    i3 = C.config.get_dynamic_batch_interval(C.config.MAX_TX_PER_BATCH + 1)
    assert i3 == C.config.MIN_BATCH_INTERVAL  # 過負荷なら最小へ固定


# ════════════════════════════════════════════════════════
# 2) dummy-save to Mongo (mongomock)
# ════════════════════════════════════════════════════════
@pytest.mark.skipif("MONGODB_URI" in os.environ, reason="本物の MongoDB がセットされている環境ではスキップ")
def test_save_tx_with_mongomock(monkeypatch: pytest.MonkeyPatch) -> None:
    import mongomock  # type: ignore
    client = mongomock.MongoClient()
    test_db = client["unit_test"]
    monkeypatch.setattr(C.db_handler, "client", client, raising=False)
    monkeypatch.setattr(C.db_handler, "db", client["unit_test"], raising=False)

    oid = C.db_handler.save_completed_tx_to_mongo(
        {"foo": "bar"},
        _db=test_db,                        # ← ★ ここで差し込み
    )
    assert oid is not None
    assert C.db_handler.db.completed_transactions.count_documents({}) == 1


# ════════════════════════════════════════════════════════
# 3) distributed storage (local json)
# ════════════════════════════════════════════════════════
def test_distributed_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)  # ./dist_storage を一時 dir に
    ok = C.distributed_storage_system.store_transaction_frag("nodeX", "tx1", "sh0", {"a": 1})
    assert ok
    data = C.distributed_storage_system.restore_transaction_frag("nodeX", "tx1", "sh0")
    assert data == {"a": 1}


# ════════════════════════════════════════════════════════
# 4) rebalance simulation
# ════════════════════════════════════════════════════════
def test_rebalance_simulation() -> None:
    moved = C.rebalancer.rebalance_once()
    # 戻り値は「移動があったノード情報のリスト」(空でも可)
    assert isinstance(moved, list)
    for entry in moved:
        assert "from" in entry and "to" in entry and "shard" in entry


# ════════════════════════════════════════════════════════
# 5) reward distribute (one-shot)
# ════════════════════════════════════════════════════════
def test_reward_distribute_once() -> None:
    before = deepcopy(C.reward_system.node_rewards)
    C.reward_system.distribute_once()
    after = C.reward_system.node_rewards

    # 少なくとも 1 ノード以上に報酬が付与される
    assert len(after) >= 1
    # どこかのノードで累計が増えているはず
    assert any(after.get(n, 0) > before.get(n, 0) for n in after)
