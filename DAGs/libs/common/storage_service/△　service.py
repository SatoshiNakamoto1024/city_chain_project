# D:\city_chain_project\network\DAGs\common\storage_service\service.py
"""
storage_service.service
───────────────────────
* StorageServiceServicerImpl : gRPC サーバ実装
* StorageClient              : 高レベルクライアント
* start_storage_server       : テスト／開発用の簡易サーバ起動ヘルパ
"""

from __future__ import annotations
import logging
import os
from concurrent import futures
from pathlib import Path
from typing import Optional
import grpc
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from common.proto import storage_pb2 as pb
from common.proto import storage_pb2_grpc as pb_grpc
from common.storage_service.distributed_storage_system import store_transaction_frag

_LOG = logging.getLogger("common.storage_service")
if not _LOG.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    _LOG.addHandler(h)
_LOG.setLevel(logging.INFO)


# ───────────────────────────────────────
# サーバ側実装
# ───────────────────────────────────────
class StorageServiceServicerImpl(pb_grpc.StorageServiceServicer):  # type: ignore
    """
    StoreFragment RPC を受け取り、ローカルディスクへ書き込むだけの簡易実装。
    """

    def __init__(self, node_id: str = "server-node"):
        self.node_id = node_id

    def StoreFragment(self, request: pb.ShardRequest, context: grpc.ServicerContext) -> pb.StoreResponse:  # noqa: N802
        # ファイル書き込み
        ok = False
        try:
            # data は bytes。ここではそのまま JSON 文字列として保存（実プロダクトでは暗号化などを検討）
            json_str = request.data.decode()
            ok = store_transaction_frag(
                node_id=self.node_id,
                tx_id=request.tx_id,
                shard_id=request.shard_id,
                data={"raw": json_str},
            )
            msg = "stored" if ok else "store failed"
        except Exception as exc:  # pylint: disable=broad-except
            _LOG.exception("StoreFragment error: %s", exc)
            ok = False
            msg = str(exc)

        return pb.StoreResponse(success=ok, message=msg)


def start_storage_server(
    port: int = 0,
    node_id: str = "server-node",
    max_workers: int = 10,
) -> tuple[grpc.Server, int]:
    """
    ・ユニットテスト／PoC 用の簡単サーバ起動ヘルパ  
    ・戻り値: (server_obj, listen_port)
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers))
    servicer = StorageServiceServicerImpl(node_id=node_id)
    pb_grpc.add_StorageServiceServicer_to_server(servicer, server)
    listen_port = server.add_insecure_port(f"localhost:{port}")
    server.start()
    _LOG.info("StorageService started on %s", listen_port)
    return server, listen_port


# ───────────────────────────────────────
# クライアント側ラッパー
# ───────────────────────────────────────
class StorageClient:
    """
    高レベルクライアント  
    ・bytes を渡すだけで StoreFragment 呼び出し  
    ・リトライは呼び出し側で必要に応じて実装
    """

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
