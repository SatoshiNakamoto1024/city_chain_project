# D:\city_chain_project\network\DAGs\common\storage_service\service.py
"""
storage_service.service  – gRPC 起動ヘルパとクライアント

* start_storage_server(port=…, node_id=…, store_func=…)
    → store_func を渡せばユニットテストで差し替え可能
* StorageClient
"""

from __future__ import annotations
import logging
from concurrent import futures
from typing import Callable, Optional
import grpc
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from common.proto import storage_pb2 as pb
from common.proto import storage_pb2_grpc as pb_grpc
from common.storage_service.storage_service_impl import (
    StorageServiceImpl,
)

_LOG = logging.getLogger(__name__)
if not _LOG.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    _LOG.addHandler(h)
_LOG.setLevel(logging.INFO)


# ─────────────────────────────────────────────
# gRPC サーバ起動ヘルパ
# ─────────────────────────────────────────────
def start_storage_server(
    *,
    port: int = 0,
    node_id: str = "server-node",
    store_func: Optional[Callable] = None,
    max_workers: int = 10,
) -> tuple[grpc.Server, int]:
    """
    Returns
    -------
    (grpc.Server, listen_port)
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers))
    servicer = StorageServiceImpl(node_id=node_id, store_func=store_func)
    pb_grpc.add_StorageServiceServicer_to_server(servicer, server)
    listen_port = server.add_insecure_port(f"localhost:{port}")
    server.start()
    _LOG.info("StorageService started on %s", listen_port)
    return server, listen_port


# ─────────────────────────────────────────────
# クライアント
# ─────────────────────────────────────────────
class StorageClient:
    """bytes を渡すだけで StoreFragment を呼ぶラッパー"""

    def __init__(self, endpoint: str):
        self.channel = grpc.insecure_channel(endpoint)
        self.stub = pb_grpc.StorageServiceStub(self.channel)

    def store_fragment(
        self,
        tx_id: str,
        shard_id: str,
        data: bytes,
        timeout: float = 5.0,
    ) -> pb.StoreResponse:
        req = pb.ShardRequest(tx_id=tx_id, shard_id=shard_id, data=data)
        return self.stub.StoreFragment(req, timeout=timeout)
