# sending_DAG/python_sending/cert_python/test_cert.py
import tempfile, os, base64
import pytest
from cert_python import (
    load_pem_cert, get_private_key_hex, get_public_key_hex,
    sign_with_cert, verify_signature_with_cert
)

# テスト用にダミー PEM を作成し、sign/verify が round-trip するかチェック
@pytest.fixture

def pem_file(tmp_path):
    # TODO: 実際の Dilithium PEM を用意するかダミーを生成
    path = tmp_path / "client.pem"
    path.write_text("""
-----BEGIN DILITHIUM PRIVATE KEY-----\n...base64...\n-----END DILITHIUM PRIVATE KEY-----\n
-----BEGIN DILITHIUM PUBLIC KEY-----\n...base64...\n-----END DILITHIUM PUBLIC KEY-----
""")
    return str(path)


def test_load_pem(pem_file):
    cert = load_pem_cert(pem_file)
    assert "priv_hex" in cert and "pub_hex" in cert


def test_sign_and_verify(pem_file):
    msg = "hello world"
    sig = sign_with_cert(msg, pem_file)
    b64 = base64.b64encode(sig).decode()
    assert verify_signature_with_cert(msg, b64, pem_file)