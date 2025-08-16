# D:\city_chain_project\network\DAGs\common\grpc_dag\tests\test_retry.py
"""
ネットワーク切断 ⇒ リトライ & バックオフ
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import time
from concurrent import futures
import grpc
from grpc_dag.gen import dag_pb2, dag_pb2_grpc
from grpc_dag.client.dag_client import DAGClient


class FlakyServicer(dag_pb2_grpc.DAGServiceServicer):
    def __init__(self):
        self.call_count = 0

    def SubmitTransaction(self, request, context):
        self.call_count += 1
        if self.call_count < 3:
            context.abort(grpc.StatusCode.UNAVAILABLE, "flaky link")
        return dag_pb2.TxResponse(status="OK", message="accepted")

    def QueryTransactionStatus(self, request, context):
        return dag_pb2.StatusResponse(status="COMPLETED")


def _start_server(servicer):
    server = grpc.server(futures.ThreadPoolExecutor(2))
    dag_pb2_grpc.add_DAGServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    return server, port


def test_retry_success():
    serv = FlakyServicer()
    server, port = _start_server(serv)

    client = DAGClient([f"localhost:{port}"])
    t0 = time.time()
    resp = client.submit_transaction("tx-retry", "{}")
    elapsed = time.time() - t0

    assert resp.status == "OK"
    assert serv.call_count == 3
    # バックオフ込みでも 5 s 以内に収束する想定
    assert elapsed < 5.0

    server.stop(0)
