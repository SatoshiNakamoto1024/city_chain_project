# D:\city_chain_project\network\DAGs\common\grpc_dag\tests\test_fuzz.py
"""
ストレス用：ランダムサイズ／ランダム文字列を 200 回送信して
❌ が出ないことを確認するだけのラフな fuzz
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import random
import string
from concurrent import futures
import grpc
from grpc_dag.gen import dag_pb2, dag_pb2_grpc
from grpc_dag.client.dag_client import DAGClient


class EchoServicer(dag_pb2_grpc.DAGServiceServicer):
    def SubmitTransaction(self, request, context):
        if len(request.payload) > 10_000:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "too big")
        return dag_pb2.TxResponse(status="OK", message="echo")

    def QueryTransactionStatus(self, request, context):
        return dag_pb2.StatusResponse(status="COMPLETED")


def _start():
    s = EchoServicer()
    server = grpc.server(futures.ThreadPoolExecutor(4))
    dag_pb2_grpc.add_DAGServiceServicer_to_server(s, server)
    p = server.add_insecure_port("localhost:0")
    server.start()
    return server, p


def random_str(n):
    return "".join(random.choice(string.ascii_letters) for _ in range(n))


def test_fuzz():
    server, port = _start()
    cli = DAGClient([f"localhost:{port}"])

    for _ in range(200):
        size = random.randint(1, 8000)
        payload = random_str(size)
        resp = cli.submit_transaction("tx-fz", payload)
        assert resp.status == "OK"

    server.stop(0)
