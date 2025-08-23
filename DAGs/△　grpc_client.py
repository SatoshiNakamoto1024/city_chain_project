# grpc_client.py
import grpc
import storage_pb2
import storage_pb2_grpc
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def get_node_endpoint(node):
    host = os.getenv("NODE_HOST", node)
    port = os.getenv("NODE_PORT", "50051")
    return f"{host}:{port}"


def send_to_node(node, tx_id, shard_id, data):
    endpoint = get_node_endpoint(node)
    channel = grpc.insecure_channel(endpoint)
    stub = storage_pb2_grpc.StorageServiceStub(channel)
    request = storage_pb2.ShardRequest(
        tx_id=tx_id,
        shard_id=str(shard_id),
        data=data.encode()
    )
    try:
        response = stub.StoreFragment(request, timeout=5)
        logger.info("[gRPC Client] %s へ送信: %s", endpoint, response.message)
        return response.success
    except grpc.RpcError as e:
        logger.error("[gRPC Client] エラー: %s", e)
        return False


if __name__ == "__main__":
    # テスト用
    print(get_node_endpoint("test_node"))
