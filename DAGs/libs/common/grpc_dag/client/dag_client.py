# D:\city_chain_project\network\DAGs\common\grpc_dag\client\dag_client.py
"""
DAGService 向けハイレベル gRPC クライアント

* 外部で生成した `grpc.Channel` をキーワード引数 `channel=` で注入しても良いし、
  エンドポイント文字列 (1 個または複数) を渡して
  `ChannelFactory.create_channel()` で自動生成しても良い。
* 共通の指数バックオフ・リトライは `retry` デコレータで提供。
"""

from __future__ import annotations

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging
from typing import List, Optional, Sequence, Union

import grpc

from grpc_dag.gen.dag_pb2 import (
    TxRequest,
    StatusRequest,
    TxResponse,
    StatusResponse,
)
from grpc_dag.gen.dag_pb2_grpc import DAGServiceStub

from grpc_dag.client.channel import ChannelFactory
from grpc_dag.client.retry import retry

# -----------------------------------------------------------------------------
# ロガー設定
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:                 # pytest で多重ハンドラ登録を防ぐ
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(_h)
log_level = os.getenv("GRPC_DAG_CLIENT_LOGLEVEL", "INFO").upper()
logger.setLevel(log_level)

# -----------------------------------------------------------------------------
# クライアント実装
# -----------------------------------------------------------------------------
class DAGClient:
    """
    Parameters
    ----------
    endpoints :
        gRPC サーバのエンドポイント文字列のリスト  
        （`str` 単体でも可）。  
        `channel` を指定した場合は無視される。
    channel :
        既に確立済みの `grpc.Channel` を直接注入したい場合に指定。
    tls_root_certificates :
        mTLS/TLS を行う場合の CA ルート証明書 (PEM バイト列)。  
        `channel` を渡した場合は無視。
    keepalive_ms :
        ChannelFactory でチャンネルを生成する場合の keep-alive インターバル (ms)。
    """

    # ---------------------------------------------------------------------
    # コンストラクタ
    # ---------------------------------------------------------------------
    def __init__(
        self,
        endpoints: Union[str, Sequence[str], None] = None,
        *,
        channel: Optional[grpc.Channel] = None,
        tls_root_certificates: Optional[bytes] = None,
        keepalive_ms: int = 10_000,
    ):
        # --------------------------
        # 1) channel を直接注入
        # --------------------------
        if channel is not None:
            self.channel: grpc.Channel = channel
            if endpoints:
                logger.warning(
                    "Both 'endpoints' and 'channel' given; endpoints are ignored."
                )

        # --------------------------
        # 2) endpoints から生成
        # --------------------------
        else:
            if endpoints is None:
                raise ValueError("Either 'endpoints' or 'channel' must be provided")

            if isinstance(endpoints, str):
                endpoints = [endpoints]
            else:
                endpoints = list(endpoints)

            self.channel = ChannelFactory.create_channel(
                endpoints=endpoints,
                tls_root_certificates=tls_root_certificates,
                keepalive_ms=keepalive_ms,
            )

        # gRPC Stub
        self.stub = DAGServiceStub(self.channel)

    # ---------------------------------------------------------------------
    # トランザクション送信
    # ---------------------------------------------------------------------
    @retry(max_attempts=4, initial_backoff=0.2)
    def submit_transaction(
        self,
        tx_id: str,
        payload: str,
        *,
        timeout: float = 5.0,
    ) -> TxResponse:
        """
        トランザクションを送信。  
        一時的な UNAVAILABLE などは `retry` デコレータで自動再試行。

        Returns
        -------
        TxResponse
        """
        req = TxRequest(tx_id=tx_id, payload=payload)
        resp: TxResponse = self.stub.SubmitTransaction(req, timeout=timeout)
        logger.debug(
            "SubmitTransaction tx_id=%s → status=%s msg=%s",
            tx_id,
            resp.status,
            resp.message,
        )
        return resp

    # ---------------------------------------------------------------------
    # ステータス照会
    # ---------------------------------------------------------------------
    @retry(max_attempts=3, initial_backoff=0.1)
    def query_transaction_status(
        self,
        tx_id: str,
        *,
        timeout: float = 3.0,
    ) -> StatusResponse:
        """
        既送信トランザクションのステータスを問い合わせ。

        Returns
        -------
        StatusResponse
        """
        req = StatusRequest(tx_id=tx_id)
        resp: StatusResponse = self.stub.QueryTransactionStatus(req, timeout=timeout)
        logger.debug("QueryTransactionStatus tx_id=%s → status=%s", tx_id, resp.status)
        return resp

    # ---------------------------------------------------------------------
    # 明示的クローズ (テストなどで便利)
    # ---------------------------------------------------------------------
    def close(self) -> None:
        """
        gRPC Channel を明示的にクローズ。
        """
        try:
            self.channel.close()  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            pass
