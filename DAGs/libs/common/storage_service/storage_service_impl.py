# D:\city_chain_project\network\DAGs\common\storage_service\storage_service_impl.py
"""
実際に gRPC リクエストを処理するクラス
依存性注入 (store_func) でユニットテストしやすく
"""
from __future__ import annotations
import logging
from typing import Callable, Optional
import grpc
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from common.proto import storage_pb2 as pb
from common.proto import storage_pb2_grpc as pb_grpc

# 既定の保存関数（本番用）
from common.storage_service.distributed_storage_system import (
    store_transaction_frag as _default_store,
)

_LOG = logging.getLogger(__name__)


class StorageServiceImpl(pb_grpc.StorageServiceServicer):
    def __init__(
        self,
        *,
        node_id: str,
        store_func: Optional[Callable] = None,
    ):
        self.node_id = node_id
        # DI: テストではここを差し替える
        self._store = store_func or _default_store

    # gRPC メソッド名は proto に合わせて CamelCase
    def StoreFragment(
        self, request: pb.ShardRequest, context: grpc.ServicerContext
    ) -> pb.StoreResponse:
        try:
            ok = self._store(
                node_id=self.node_id,
                tx_id=request.tx_id,
                shard_id=request.shard_id,
                data={"raw": request.data.decode()},
            )
            return pb.StoreResponse(success=ok, message="stored" if ok else "fail")
        except Exception as exc:  # pragma: no cover
            _LOG.exception("StoreFragment error: %s", exc)
            return pb.StoreResponse(success=False, message=str(exc))
