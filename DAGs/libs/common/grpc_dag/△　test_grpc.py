# D:\city_chain_project\network\sending_DAGs\python_sending\common\grpc\test_grpc.py
#!/usr/bin/env python3
"""
gRPC クライアント／サーバ ユニットテスト
- 1回目失敗→2回目成功のリトライ動作を検証
- ステータス照会の正常系動作を検証
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import grpc
import pytest
from concurrent import futures

from grpc_dag.dag_pb2 import TxRequest, TxResponse, StatusRequest, StatusResponse
from grpc_dag.dag_pb2_grpc import DAGServiceServicer, add_DAGServiceServicer_to_server
from network.sending_DAG.python_sending.common.grpc_dag.server.app_grpc import GRPCClient

class DummyDAGServicer(DAGServiceServicer):
    def __init__(self):
        self.submit_count = 0

    def SubmitTransaction(self, request, context):
        self.submit_count += 1
        if self.submit_count == 1:
            context.abort(grpc.StatusCode.UNAVAILABLE, "Transient failure")
        return TxResponse(status="OK", message=f"Received {request.tx_id}")

    def QueryTransactionStatus(self, request, context):
        return StatusResponse(status="COMPLETED")

@pytest.fixture(scope="module")
def grpc_server():
    servicer = DummyDAGServicer()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    add_DAGServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port('localhost:0')
    server.start()
    time.sleep(0.5)
    yield servicer, port
    server.stop(True)

def test_submit_transaction_with_retry(grpc_server):
    servicer, port = grpc_server
    client = GRPCClient(f'localhost:{port}')
    resp = client.submit_transaction('tx1', 'data')
    assert resp.status == 'OK'
    assert servicer.submit_count == 2

def test_query_transaction_status(grpc_server):
    _, port = grpc_server
    client = GRPCClient(f'localhost:{port}')
    status = client.query_transaction_status('tx2')
    assert status.status == 'COMPLETED'
