# D:\city_chain_project\network\DAGs\common\storage_service\test_storage_service.py
"""
E2E テスト – fake store_func を DI して呼び出し確認
"""
from __future__ import annotations

import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from storage_service.service import (
    start_storage_server,
    StorageClient,
)

_calls: list[tuple] = []


def _fake_store(node_id, tx_id, shard_id, data):
    _calls.append((node_id, tx_id, shard_id, data))
    return True


@pytest.mark.asyncio
async def test_store_fragment():
    server, port = start_storage_server(
        port=0,
        node_id="test-node",
        store_func=_fake_store,  # ← 依存性注入
    )
    try:
        cli = StorageClient(f"localhost:{port}")
        resp = cli.store_fragment("tx-123", "S0", b'{"k":"v"}')
        assert resp.success

        assert _calls, "fake store_transaction_frag was not called"
        node_id, tx_id, shard_id, data = _calls[0]
        assert (node_id, tx_id, shard_id) == ("test-node", "tx-123", "S0")
        assert data == {"raw": '{"k":"v"}'}
    finally:
        server.stop(0)
