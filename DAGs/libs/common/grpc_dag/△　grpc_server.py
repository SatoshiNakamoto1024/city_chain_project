# D:\city_chain_project\network\sending_DAGs\python_sending\common\grpc\grpc_server.py

"""
grpc_server.py

gRPCサーバ側の処理。ノードが起動して、StoreFragmentリクエストを受け取り
ローカルに保存するなど行う。
"""

import grpc
from concurrent import futures
import logging
import os
import json

import storage_pb2
import storage_pb2_grpc

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)

class StorageService(storage_pb2_grpc.StorageServiceServicer):
    def StoreFragment(self, request, context):
        node_id = os.getenv("NODE_ID", "default_node")
        base_path = f"./grpc_node_storage/{node_id}"
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)

        data_dict = {
            "tx_id": request.tx_id,
            "shard_id": request.shard_id,
            "fragment_data": request.data.decode("utf-8")
        }
        filename = os.path.join(base_path, f"{request.tx_id}_{request.shard_id}.json")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
            logger.info("[gRPC Server|%s] StoreFragment OK: %s", node_id, filename)
        except Exception as e:
            logger.error("[gRPC Server|%s] 保存エラー: %s", node_id, e)
            return storage_pb2.StoreResponse(success=False, message="保存失敗")

        return storage_pb2.StoreResponse(success=True, message="Shard stored successfully")

def serve():
    """
    ノードとしてgRPCサーバを起動。
    NODE_PORT 環境変数でポート指定できる。
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    storage_pb2_grpc.add_StorageServiceServicer_to_server(StorageService(), server)
    port = os.getenv("NODE_PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info("[gRPC Server] ノード起動: port=%s node_id=%s", port, os.getenv("NODE_ID", "default_node"))

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("[gRPC Server] 停止")
        server.stop(0)

if __name__ == "__main__":
    serve()
