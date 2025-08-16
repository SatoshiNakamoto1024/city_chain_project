# network/DAGs/common/security/mtls.py
"""
mtls.py
────────
mTLS（双方向 TLS）対応の
  • HTTPS セッション (`requests.Session`)
  • gRPC チャンネル (`grpc.Channel`)
を生成するヘルパー。

ポイント
---------
* **毎回 os.getenv(...) でパスを取得** するため、
  `pytest.monkeypatch.setenv()` や本番環境の
  実行時環境変数の変更がそのまま反映される。
* デフォルト値は Linux 想定の
  `/etc/ssl/{client.crt,client.key,ca.crt}`。
"""

from __future__ import annotations

import os
from typing import Tuple

import grpc
import requests

from . import config


# ────────────────────────────────────────────────
# 内部ユーティリティ
# ────────────────────────────────────────────────
def _get_cert_paths() -> Tuple[str, str, str]:
    """
    現在の環境変数から
      (client_cert_path, client_key_path, ca_cert_path)
    を取得して返す。
    """
    cert = os.getenv(config.CLIENT_CERT_ENV, "/etc/ssl/client.crt")
    key  = os.getenv(config.CLIENT_KEY_ENV,  "/etc/ssl/client.key")
    ca   = os.getenv(config.CA_CERT_ENV,     "/etc/ssl/ca.crt")
    return cert, key, ca


# ────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────
def create_https_session() -> requests.Session:
    """
    mTLS 設定済みの `requests.Session` を返す。

    Notes
    -----
    * `session.cert` に `(client_cert, client_key)` をセット。
    * `session.verify` に `ca_cert` をセット。
    """
    client_cert, client_key, ca_cert = _get_cert_paths()

    sess = requests.Session()
    sess.cert = (client_cert, client_key)
    sess.verify = ca_cert
    return sess


def create_grpc_channel(
    target: str,
    *,
    override_authority: str | None = None,
    options: list[tuple[str, str | int]] | None = None,
) -> grpc.Channel:
    """
    mTLS 認証付き `grpc.secure_channel` を生成して返す。

    Parameters
    ----------
    target
        "host:port" 形式。
    override_authority
        証明書の CommonName と異なる IP 直打ち接続などを
        行う場合に指定する。
    options
        gRPC チャンネルオプションを追加したい場合に指定。
    """
    client_cert, client_key, ca_cert = _get_cert_paths()

    with open(client_cert, "rb") as f:
        certificate_chain = f.read()
    with open(client_key, "rb") as f:
        private_key = f.read()
    with open(ca_cert, "rb") as f:
        root_cert = f.read()

    creds = grpc.ssl_channel_credentials(
        root_certificates=root_cert,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )

    opts = list(options or [])
    if override_authority:
        opts.append(("grpc.ssl_target_name_override", override_authority))

    return grpc.secure_channel(target, creds, options=opts)


__all__ = [
    "create_https_session",
    "create_grpc_channel",
]
