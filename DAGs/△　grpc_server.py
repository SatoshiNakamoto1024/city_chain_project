# grpc_server.py
import grpc
from concurrent import futures
import time
import os
import json
import logging
import storage_pb2
import storage_pb2_grpc

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class StorageService(storage_pb2_grpc.StorageServiceServicer):
    def StoreFragment(self, request, context):
        node_id = os.getenv("NODE_ID", "default_node")
        base_path = f"./node_storage/{node_id}"
        os.makedirs(base_path, exist_ok=True)
        data = {
            "tx_id": request.tx_id,
            "sender": request.sender,
            "receiver": request.receiver,
            "amount": request.amount,
            "timestamp": request.timestamp,
            "hash": request.hash,
            "distribution_info": request.distribution_info,
            "fragment_data": request.fragment_data.decode('utf-8')
        }
        filename = os.path.join(base_path, f"{request.tx_id}.json")
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("[Node %s] 保存完了: %s", node_id, filename)
        except Exception as e:
            logger.error("[Node %s] 保存エラー: %s", node_id, e)
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return storage_pb2.StoreResponse(success=False, message="保存失敗")
        return storage_pb2.StoreResponse(success=True, message="Fragment stored successfully.")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    storage_pb2_grpc.add_StorageServiceServicer_to_server(StorageService(), server)
    port = os.getenv("NODE_PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info("[gRPC Server] ノードが起動: ポート %s", port)
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        logger.info("サーバー停止中...")
        server.stop(0)

if __name__ == "__main__":
    serve()
