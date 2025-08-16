# D:\city_chain_project\network\DAGs\common\grpc_dag\tests\test_tls.py

"""
最小限の mTLS ハンドシェイクテスト（自己署名証明書）
OpenSSL 依存のため CI では `GRPC_SKIP_TLS_TEST=1` でスキップ可
"""
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import ssl
import tempfile
import subprocess
from concurrent import futures
import grpc
import pytest

from grpc_dag.gen import dag_pb2, dag_pb2_grpc
from grpc_dag.client.channel import ChannelFactory
from grpc_dag.client.dag_client import DAGClient

SKIP = os.getenv("GRPC_SKIP_TLS_TEST")

@pytest.mark.skipif(SKIP, reason="TLS test skipped")
def test_tls_round_trip():
    """
    - 動的に自己署名証明書を生成（OpenSSL 必須）
    - サーバ側：ssl_server_credentials で起動
    - クライアント側：ChannelFactory.create_secure_channel で接続
    - DAGClient 経由で SubmitTransaction が通ることを確認
    """
    with tempfile.TemporaryDirectory() as td:
        # 証明書・鍵のパス
        crt = os.path.join(td, "crt.pem")
        key = os.path.join(td, "key.pem")

        # OpenSSL で自己署名証明書を生成（CN を localhost にセット）
        subprocess.check_call([
            "openssl", "req", "-newkey", "rsa:2048", "-nodes", "-x509",
            "-subj", "/CN=localhost",  # <<-- ここを localhost に変更
            "-days", "1",
            "-keyout", key, "-out", crt
        ])

        # サーバ側の SSL 認証情報をロード
        with open(key, "rb") as kf, open(crt, "rb") as cf:
            server_creds = grpc.ssl_server_credentials([(kf.read(), cf.read())])

        # サーバ実装：Echo サービス
        class EchoServicer(dag_pb2_grpc.DAGServiceServicer):
            def SubmitTransaction(self, request, context):
                return dag_pb2.TxResponse(status="OK", message="tls")
            def QueryTransactionStatus(self, request, context):
                return dag_pb2.StatusResponse(status="COMPLETED")

        # gRPC サーバ起動 (TLS)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        dag_pb2_grpc.add_DAGServiceServicer_to_server(EchoServicer(), server)
        port = server.add_secure_port("localhost:0", server_creds)
        server.start()
        time.sleep(0.5)  # サーバ起動待ち

        # クライアント用チャンネルを明示的に生成
        with open(crt, "rb") as cf:
            root_certs = cf.read()
        chan = ChannelFactory.create_secure_channel(
            endpoint=f"localhost:{port}",
            tls_root_certificates=root_certs,
            keepalive_ms=5000
        )

        # DAGClient にチャンネルを注入
        cli = DAGClient(channel=chan)

        # 実際に SubmitTransaction を呼び出す
        resp = cli.submit_transaction("tls-1", "{}", timeout=2.0)
        assert resp.status == "OK"
        assert resp.message == "tls"

        server.stop(0)
