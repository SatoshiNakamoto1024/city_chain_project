# city_chain_project\network\DAGs\common\transport\grpc_transport.py
"""
gRPC トランスポート層 (HTTP/2 + バイナリ) のクライアント／サーバー抽象化
"""
from __future__ import annotations
import grpc
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence, Type
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class GRPCClient:
    """
    gRPC クライアントラッパー

    Parameters
    ----------
    stub_class : Type
        grpcio-tools で生成された `*Stub` クラス
    endpoints : Sequence[str]
        ["host1:port", "host2:port", …]
    tls_root_certificates : Optional[bytes]
        CA ルート証明書 (PEM バイト列)。None で平文チャンネル。
    keepalive_ms : int
        gRPC keepalive インターバル (ms)
    """

    def __init__(
        self,
        stub_class: Type,
        endpoints: Sequence[str] | str,
        tls_root_certificates: bytes | None = None,
        keepalive_ms: int = 10_000,
    ):
        if isinstance(endpoints, str):
            endpoints = [endpoints]
        self._endpoint = endpoints[0]
        self.channel = self._create_channel(self._endpoint, tls_root_certificates, keepalive_ms)
        self.stub = stub_class(self.channel)

    def _create_channel(
        self,
        endpoint: str,
        tls_root_certificates: bytes | None,
        keepalive_ms: int,
    ) -> grpc.Channel:
        options = [
            ("grpc.keepalive_time_ms", keepalive_ms),
            ("grpc.keepalive_timeout_ms", 5000),
            ("grpc.keepalive_permit_without_calls", 1),
        ]
        if tls_root_certificates:
            creds = grpc.ssl_channel_credentials(root_certificates=tls_root_certificates)
            return grpc.secure_channel(endpoint, creds, options)
        else:
            return grpc.insecure_channel(endpoint, options)

    def close(self) -> None:
        """チャンネルを閉じる"""
        try:
            self.channel.close()  # type: ignore[attr-defined]
        except Exception:
            pass


class GRPCServer:
    """
    gRPC サーバーラッパー

    Parameters
    ----------
    servicer :
        grpcio-tools で生成された `*Servicer` を継承した実装クラスのインスタンス
    add_servicer_fn :
        `add_*Servicer_to_server` 関数
    port : int
        待ち受けポート (0 で自動選択)
    tls_cert : Optional[bytes]
        サーバー証明書チェーン (PEM)
    tls_key : Optional[bytes]
        サーバー秘密鍵 (PEM)
    interceptors : Optional[list[grpc.ServerInterceptor]]
        サーバー側インターセプタ
    max_workers : int
        スレッドプールのワーカー数
    """

    def __init__(
        self,
        servicer: object,
        add_servicer_fn: callable,
        *,
        port: int = 50051,
        tls_cert: bytes | None = None,
        tls_key: bytes | None = None,
        interceptors: list[grpc.ServerInterceptor] | None = None,
        max_workers: int = 10,
    ):
        server = grpc.server(
            ThreadPoolExecutor(max_workers),
            interceptors=interceptors or [],
        )
        add_servicer_fn(servicer, server)

        if tls_cert and tls_key:
            creds = grpc.ssl_server_credentials(
                [(tls_key, tls_cert)],
                # クライアント認証を要求する場合は下記:
                # root_certificates=ca_root, require_client_auth=True
            )
            self._port = server.add_secure_port(f"[::]:{port}", creds)
        else:
            self._port = server.add_insecure_port(f"[::]:{port}")

        self._server = server

    def start(self) -> None:
        """サーバーを起動"""
        self._server.start()

    def stop(self, grace: int = 0) -> None:
        """サーバーを停止"""
        self._server.stop(grace)

    def wait_for_termination(self) -> None:
        """サーバー終了まで待機"""
        self._server.wait_for_termination()

    @property
    def port(self) -> int:
        return self._port
