# D:\city_chain_project\network\DAGs\common\grpc_dag\client\channel.py
"""
ChannelFactory: gRPC チャンネルを生成するユーティリティ
- keepalive 設定
- (m)TLS 設定
- 将来的にロードバランシング対応など拡張可
"""

import grpc
from typing import List, Optional

class ChannelFactory:
    @staticmethod
    def create_secure_channel(
        endpoint: str,
        tls_root_certificates: bytes,
        keepalive_ms: int = 10000
    ) -> grpc.Channel:
        """
        TLS 有効チャンネルを生成。CA ルート証明書を指定。
        """
        options = [
            ('grpc.keepalive_time_ms', keepalive_ms),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', 1),
        ]
        creds = grpc.ssl_channel_credentials(root_certificates=tls_root_certificates)
        return grpc.secure_channel(endpoint, creds, options)

    @staticmethod
    def create_insecure_channel(
        endpoint: str,
        keepalive_ms: int = 10000
    ) -> grpc.Channel:
        """
        TLS 無効 (平文) チャンネルを生成。
        """
        options = [
            ('grpc.keepalive_time_ms', keepalive_ms),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', 1),
        ]
        return grpc.insecure_channel(endpoint, options)

    @staticmethod
    def create_channel(
        endpoints: List[str],
        tls_root_certificates: Optional[bytes] = None,
        keepalive_ms: int = 10000
    ) -> grpc.Channel:
        """
        シンプルに最初のエンドポイントでチャンネルを生成。
        将来的に複数エンドポイントの LB にも対応可。
        """
        endpoint = endpoints[0]
        if tls_root_certificates:
            return ChannelFactory.create_secure_channel(endpoint, tls_root_certificates, keepalive_ms)
        else:
            return ChannelFactory.create_insecure_channel(endpoint, keepalive_ms)
