# D:\city_chain_project\network\DAGs\common\grpc_dag\tests\test_concurrency.py
"""
100 同時送信でキュー／ワーカーが枯渇しないか
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from concurrent import futures
import grpc
import threading
from grpc_dag.gen import dag_pb2, dag_pb2_grpc
from grpc_dag.client.dag_client import DAGClient


class CounterServicer(dag_pb2_grpc.DAGServiceServicer):
    def __init__(self):
        self.lock = threading.Lock()
        self.cnt = 0

    def SubmitTransaction(self, request, context):
        with self.lock:
            self.cnt += 1
        return dag_pb2.TxResponse(status="OK", message="x")

    def QueryTransactionStatus(self, request, context):
        return dag_pb2.StatusResponse(status="COMPLETED")


def test_concurrency():
    serv = CounterServicer()
    svr = grpc.server(futures.ThreadPoolExecutor(50))
    dag_pb2_grpc.add_DAGServiceServicer_to_server(serv, svr)
    port = svr.add_insecure_port("localhost:0")
    svr.start()

    cli = DAGClient([f"localhost:{port}"])  # ← 修正

    def send(i):
        cli.submit_transaction(f"tx{i}", "{}")

    with futures.ThreadPoolExecutor(50) as pool:
        list(pool.map(send, range(100)))

    assert serv.cnt == 100
    svr.stop(0)
