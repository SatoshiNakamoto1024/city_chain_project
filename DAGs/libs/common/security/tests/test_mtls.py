# network/DAGs/common/security/tests/test_mtls.py
import pytest
import os, sys
sys.path.append(os.path.abspath("D:\\city_chain_project\\network\\DAGs\\common"))

from security import mtls, config

def test_create_https_session(tmp_path, monkeypatch):
    # 環境変数パスを一時ファイルに向ける
    crt = tmp_path/"c.crt"; crt.write_bytes(b"dummy")
    key = tmp_path/"c.key"; key.write_bytes(b"dummy")
    ca  = tmp_path/"ca.crt"; ca.write_bytes(b"dummy")
    monkeypatch.setenv("CLIENT_CERT_PATH", str(crt))
    monkeypatch.setenv("CLIENT_KEY_PATH",  str(key))
    monkeypatch.setenv("CA_CERT_PATH",      str(ca))
    sess = mtls.create_https_session()
    assert sess.cert == (str(crt), str(key))
    assert sess.verify == str(ca)

def test_create_grpc_channel(tmp_path, monkeypatch):
    # ダミー証明書を作ってパッチ
    crt = tmp_path/"a.crt"; crt.write_bytes(b"dummy")
    key = tmp_path/"a.key"; key.write_bytes(b"dummy")
    ca  = tmp_path/"ca.crt"; ca.write_bytes(b"dummy")
    monkeypatch.setenv("CLIENT_CERT_PATH", str(crt))
    monkeypatch.setenv("CLIENT_KEY_PATH",  str(key))
    monkeypatch.setenv("CA_CERT_PATH",      str(ca))
    ch = mtls.create_grpc_channel("localhost:12345")
    # secure_channel オブジェクトが返る
    assert hasattr(ch, "close")
