# D:\city_chain_project\network\DAGs\common\grpc_dag\server\app_grpc.py
"""
gRPC クライアントラッパー (本番運用向け)
- TLS 対応
- キープアライブ設定
- リトライ (指数バックオフ)
- デフォルトデッドライン
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import time
import grpc
import logging
from typing import Optional
from grpc_dag.gen.dag_pb2 import TxRequest, TxResponse, StatusRequest, StatusResponse
from grpc_dag.gen.dag_pb2_grpc import DAGServiceStub

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class GRPCClient:
    def __init__(
        self,
        endpoint: str,
        tls_root_certificates: Optional[bytes] = None,
        keepalive_ms: int = 10000,
    ):
        self.endpoint = endpoint
        self.channel = self._create_channel(tls_root_certificates, keepalive_ms)
        self.stub = DAGServiceStub(self.channel)

    def _create_channel(
        self,
        tls_root_certificates: Optional[bytes],
        keepalive_ms: int,
    ) -> grpc.Channel:
        options = [
            ('grpc.keepalive_time_ms', keepalive_ms),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', 1),
        ]
        if tls_root_certificates:
            creds = grpc.ssl_channel_credentials(root_certificates=tls_root_certificates)
            return grpc.secure_channel(self.endpoint, creds, options)
        else:
            return grpc.insecure_channel(self.endpoint, options)

    def submit_transaction(
        self,
        tx_id: str,
        data: str,
        timeout: float = 5.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> TxResponse:
        req = TxRequest(tx_id=tx_id, payload=data)
        for attempt in range(1, max_retries + 1):
            try:
                start = time.time()
                resp = self.stub.SubmitTransaction(req, timeout=timeout)
                elapsed = time.time() - start
                logger.info(f"SubmitTransaction succeeded in {elapsed:.2f}s: tx_id={tx_id}")
                return resp
            except grpc.RpcError as e:
                code, detail = e.code(), e.details()
                logger.warning(f"Attempt {attempt} failed: {code} - {detail}")
                # 再試行対象のステータスコードのみリトライ
                if attempt == max_retries or code not in (
                    grpc.StatusCode.UNAVAILABLE,
                    grpc.StatusCode.DEADLINE_EXCEEDED,
                    grpc.StatusCode.RESOURCE_EXHAUSTED
                ):
                    logger.error("No more retries, raising.")
                    raise
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                logger.info(f"Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)

    def query_transaction_status(
        self,
        tx_id: str,
        timeout: float = 3.0,
    ) -> StatusResponse:
        req = StatusRequest(tx_id=tx_id)
        try:
            return self.stub.QueryTransactionStatus(req, timeout=timeout)
        except grpc.RpcError as e:
            logger.error(f"QueryTransactionStatus failed: {e.code()} - {e.details()}")
            raise
