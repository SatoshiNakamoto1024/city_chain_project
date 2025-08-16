# D:\city_chain_project\network\DAGs\common\node_list\test_node_list.py
"""
pytest -v common/node_list/tests/test_node_list.py

Redis に依存しない純粋ユニットテスト。
環境変数で BACKEND=redis を指定し、FakeRedisBackend で差し替え。
"""
import asyncio
import time
from typing import List
import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 環境変数で redis backend を指定（manager.py 内部ロジック用）
os.environ["PRESENCE_BACKEND"] = "redis"

from node_list.schemas import NodeInfo
from node_list.registry import get_registry
from node_list.manager import NodeListManager

# -----------------------------------------------------------------
# Fake backend （Redis/HTTP 共通で使える最小モック）
# -----------------------------------------------------------------
class FakePresenceBackend:
    def __init__(self):
        self._set = set()

    async def login(self, node_id: str):
        self._set.add(node_id)

    async def logout(self, node_id: str):
        self._set.discard(node_id)

    async def heartbeat(self, node_id: str):
        pass

    async def list_nodes(self) -> List[NodeInfo]:
        now = time.time()
        return [NodeInfo(node_id=n, last_seen=now) for n in sorted(self._set)]

# -----------------------------------------------------------------
# テスト
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_registry_roundtrip(monkeypatch):
    mgr = NodeListManager()
    # backend 差し替え
    monkeypatch.setattr(mgr, "_backend", FakePresenceBackend())

    # login → registry 更新
    await mgr._backend.login("node-A")
    nodes = await mgr._backend.list_nodes()
    await get_registry().update(nodes)

    # registry 取得
    stored = await get_registry().get_nodes()
    assert len(stored) == 1
    assert stored[0].node_id == "node-A"
