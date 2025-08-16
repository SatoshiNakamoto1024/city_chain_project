# D:\city_chain_project\network\sending_DAGs\python_sending\common\grpc_dag\client\channel.py
import grpc
from typing import List, Optional


class ChannelFactory:
    """
    gRPC Channel の生成を集中管理。
    - エンドポイントのロードバランシング (カンマ区切りで複数可)
    - TLS/mTLS (root_certificates)
    - Keepalive オプション設定
    """

    @staticmethod
    def create_channel(
        endpoints: List[str],
        tls_root_certificates: Optional[bytes] = None,
        keepalive_ms: int = 10000,
    ) -> grpc.Channel:
        # gRPC チャンネルオプション
        options = [
            ('grpc.keepalive_time_ms', keepalive_ms),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', 1),
            ('grpc.min_reconnect_backoff_ms', 1000),
            ('grpc.max_reconnect_backoff_ms', 120000),
        ]
        target = ",".join(endpoints)
        if tls_root_certificates:
            creds = grpc.ssl_channel_credentials(root_certificates=tls_root_certificates)
            return grpc.secure_channel(target, creds, options)
        else:
            return grpc.insecure_channel(target, options)
