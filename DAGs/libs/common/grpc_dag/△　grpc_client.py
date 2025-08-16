# D:\city_chain_project\network\sending_DAGs\python_sending\common\grpc\grpc_client.py

"""
grpc_client.py

gRPCクライアント側の処理。
分散ストレージやノード間通信を行う際に使用する例。
本番ではノードのホスト/ポート管理、TLS設定などをちゃんと行う必要がある。
"""

import grpc
import logging
import os
import storage_pb2
import storage_pb2_grpc

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)

def get_node_endpoint(node_id: str):
    """
    ノードIDからホスト・ポートを導く例。
    環境変数やDBで管理するなど実装に応じて変更。
    ここでは簡易に "localhost:50051" を返すスタブ。
    """
    host = os.getenv("NODE_HOST", "localhost")
    port = os.getenv("NODE_PORT", "50051")
    return f"{host}:{port}"

def send_shard_to_node(node_info: dict, tx_id: str, shard_id: str, data: str) -> bool:
    """
    shardデータをノードへgRPCで送る例。
    node_info: {"node_id":..., "weight":..., ...}
    """
    endpoint = get_node_endpoint(node_info["node_id"])
    channel = grpc.insecure_channel(endpoint)
    stub = storage_pb2_grpc.StorageServiceStub(channel)

    request = storage_pb2.ShardRequest(
        tx_id=tx_id,
        shard_id=shard_id,
        data=data.encode("utf-8")
    )
    try:
        response = stub.StoreFragment(request, timeout=5)
        logger.info("[gRPC Client] Shard送信: node=%s, shard_id=%s, result=%s", node_info["node_id"], shard_id, response.message)
        return response.success
    except grpc.RpcError as e:
        logger.error("[gRPC Client] gRPCエラー: %s", e)
        return False
