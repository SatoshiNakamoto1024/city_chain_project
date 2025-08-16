# D:\city_chain_project\network\DAGs\common\grpc_dag\tests\test_timeout.py
"""
デッドライン超過 (サーバ遅延 → DEADLINE_EXCEEDED) を検証
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import time, pytest
from concurrent import futures
import grpc
from grpc_dag.gen import dag_pb2, dag_pb2_grpc
from grpc_dag.client.dag_client import DAGClient


class SlowServicer(dag_pb2_grpc.DAGServiceServicer):
    def SubmitTransaction(self, request, context):
        time.sleep(2.5)  # 意図的に遅延
        return dag_pb2.TxResponse(status="OK", message="slow-ok")

    def QueryTransactionStatus(self, request, context):
        return dag_pb2.StatusResponse(status="COMPLETED")


def _srv():
    servicer = SlowServicer()
    server = grpc.server(futures.ThreadPoolExecutor(2))
    dag_pb2_grpc.add_DAGServiceServicer_to_server(servicer, server)
    p = server.add_insecure_port("localhost:0")
    server.start()
    return server, p


def test_deadline():
    server, port = _srv()
    cli = DAGClient([f"localhost:{port}"])
    with pytest.raises(grpc.RpcError) as err:
        cli.submit_transaction("slow1", "{}", timeout=1.0)  # 1 s
    assert err.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED
    server.stop(0)
