# D:\city_chain_project\network\DAGs\common\grpc_dag\server\servicer.py
"""
gRPC サーバー起動スクリプト (本番用)
- DAGService を提供
- キープアライブ設定
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import logging
from concurrent import futures
import grpc
from common.grpc_dag.gen.dag_pb2 import TxResponse, StatusResponse
from common.grpc_dag.gen.dag_pb2_grpc import DAGServiceServicer, add_DAGServiceServicer_to_server

# ビジネスロジックを実装するクラスをインポート
from sending_DAG.python_sending.municipality_level.municipality_dag_handler import CityDAGHandler

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class DAGServiceServicerImpl(DAGServiceServicer):
    def __init__(self, handler: CityDAGHandler):
        self.handler = handler

    def SubmitTransaction(self, request, context):
        try:
            tx_id, tx_hash = self.handler.add_transaction(
                sender=request.tx_id,  # 例: use tx_id as sender for demo
                receiver=request.payload,  # 例: payload as receiver
                amount=0.0
            )
            return TxResponse(status="PENDING", message=f"Queued {tx_id}")
        except Exception as e:
            logger.exception("SubmitTransaction error")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def QueryTransactionStatus(self, request, context):
        # 例として常に COMPLETED を返す
        return StatusResponse(status="COMPLETED")

def serve(port: int = 50051, max_workers: int = 10):
    handler = CityDAGHandler(city_name="NewYork")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers), options=[
        ('grpc.keepalive_time_ms', 10000),
        ('grpc.keepalive_timeout_ms', 5000),
        ('grpc.keepalive_permit_without_calls', 1),
    ])
    add_DAGServiceServicer_to_server(DAGServiceServicerImpl(handler), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info(f"gRPC server listening on port {port}...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
