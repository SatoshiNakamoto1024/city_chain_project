# D:\city_chain_project\network\sending_DAGs\python_sending\common\grpc_dag\client\dag_client.py

import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging
from typing import List, Optional

from grpc_dag.gen.dag_pb2 import TxRequest, StatusRequest
from grpc_dag.gen.dag_pb2_grpc import DAGServiceStub
from grpc_dag.client.channel import ChannelFactory
from grpc_dag.client.retry import retry

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class DAGClient:
    """
    DAGService 向け高レベルクライアント。
    - ChannelFactory 経由でチャンネル構築
    - retry デコレータ適用
    """

    def __init__(
        self,
        endpoints: List[str],
        tls_root_certificates: Optional[bytes] = None,
        keepalive_ms: int = 10000,
    ):
        # エンドポイントのリストを受け取ってラウンドロビン or 負荷分散されたチャンネルを生成
        self.channel = ChannelFactory.create_channel(
            endpoints, tls_root_certificates, keepalive_ms
        )
        self.stub = DAGServiceStub(self.channel)

    @retry(max_attempts=4, initial_backoff=0.2)
    def submit_transaction(
        self,
        tx_id: str,
        payload: str,
        timeout: float = 5.0
    ):
        """
        トランザクションを送信。
        成功まで retry デコレータが再試行。
        """
        req = TxRequest(tx_id=tx_id, payload=payload)
        start_ts = time.time()
        resp = self.stub.SubmitTransaction(req, timeout=timeout)
        elapsed = time.time() - start_ts
        logger.info(
            f"SubmitTransaction succeeded in {elapsed:.2f}s: "
            f"tx_id={tx_id}, status={resp.status}"
        )
        return resp

    @retry(max_attempts=3, initial_backoff=0.1)
    def query_transaction_status(
        self,
        tx_id: str,
        timeout: float = 3.0
    ):
        """
        トランザクションのステータスを問い合わせ。
        """
        req = StatusRequest(tx_id=tx_id)
        start_ts = time.time()
        resp = self.stub.QueryTransactionStatus(req, timeout=timeout)
        elapsed = time.time() - start_ts
        logger.info(
            f"QueryTransactionStatus succeeded in {elapsed:.2f}s: "
            f"tx_id={tx_id}, status={resp.status}"
        )
        return resp
