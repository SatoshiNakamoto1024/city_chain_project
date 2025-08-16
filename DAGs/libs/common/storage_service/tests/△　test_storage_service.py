# D:\city_chain_project\network\sending_DAGs\python_sending\common\storage_service\tests\test_storage_service.py
"""
storage_service のユニットテスト
"""
from __future__ import annotations
import json
import time
import grpc
import pytest

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from storage_service.service import StorageClient, start_storage_server

# ───────────────────────────────────────
# サーバ起動（module スコープで 1 度だけ）
# ───────────────────────────────────────
@pytest.fixture(scope="module")
def grpc_storage_server():
    server, port = start_storage_server(port=0, node_id="test-node")
    # サーバが立ち上がるまで小休止
    time.sleep(0.3)
    yield port
    server.stop(0)


# ───────────────────────────────────────
# 1) 正常系: StoreFragment → success True
# ───────────────────────────────────────
def test_store_fragment_success(grpc_storage_server):
    cli = StorageClient(f"localhost:{grpc_storage_server}")
    payload = json.dumps({"foo": "bar"}).encode()

    resp = cli.store_fragment("tx-999", "0", payload, timeout=2.0)
    assert resp.success is True
    assert resp.message == "stored"
