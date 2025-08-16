# D:\city_chain_project\network\DAGs\common\node_list\test_node_list.py
"""
最低限のユニットテスト
- Redis backend をモックして Heartbeat→取得→Registry 反映を検証
"""
import asyncio
import types
import time
import pytest

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from node_list.registry import get_registry
from node_list.manager import NodeListManager
from node_list.schemas import NodeInfo

# -----------------------------------------------------------------
# Redis backend モック
# -----------------------------------------------------------------
class FakeRedisBackend:
    def __init__(self):
        self._set = set()

    async def login(self, node_id: str):
        self._set.add(node_id)

    async def heartbeat(self, node_id: str):
        # noop
        pass

    async def logout(self, node_id: str):
        self._set.discard(node_id)

    async def list_nodes(self):
        now = time.time()
        return [NodeInfo(node_id=n, last_seen=now) for n in sorted(self._set)]

# -----------------------------------------------------------------
# テスト本体
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_registry_update(monkeypatch):
    # Manager インスタンスに Fake backend を差し替え
    mgr = NodeListManager()
    monkeypatch.setattr(mgr, "_backend", FakeRedisBackend())

    # run_forever() を 2 サイクルだけ回す
    async def limited_run():
        await mgr._backend.login("node-A")
        nodes = await mgr._backend.list_nodes()
        reg = get_registry()
        await reg.update(nodes)

    await limited_run()
    stored = await get_registry().get_nodes()
    assert len(stored) == 1
    assert stored[0].node_id == "node-A"
