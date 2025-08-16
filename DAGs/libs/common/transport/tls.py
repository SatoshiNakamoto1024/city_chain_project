# city_chain_project\network\DAGs\common\transport\tls.py
"""
mTLS 用証明書ロード／生成ユーティリティ
"""
from __future__ import annotations
from pathlib import Path
import grpc


def load_client_credentials(
    root_cert: Path,
    private_key: Path,
    cert_chain: Path,
) -> grpc.ChannelCredentials:
    """
    クライアント用 TLS 証明書を読み込み
    """
    root = root_cert.read_bytes()
    key = private_key.read_bytes()
    cert = cert_chain.read_bytes()
    return grpc.ssl_channel_credentials(
        root_certificates=root,
        private_key=key,
        certificate_chain=cert,
    )


def load_server_credentials(
    private_key: Path,
    cert_chain: Path,
    ca_root: Path | None = None,
) -> grpc.ServerCredentials:
    """
    サーバー用 TLS 証明書を読み込み (クライアント認証 optional)
    """
    key = private_key.read_bytes()
    cert = cert_chain.read_bytes()
    if ca_root:
        root = ca_root.read_bytes()
        return grpc.ssl_server_credentials(
            [(key, cert)],
            root_certificates=root,
            require_client_auth=True,
        )
    else:
        return grpc.ssl_server_credentials([(key, cert)])
