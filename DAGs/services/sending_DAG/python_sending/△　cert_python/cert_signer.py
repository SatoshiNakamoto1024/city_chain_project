# sending_DAG/python_sending/cert_python/cert_signer.py
"""
Dilithium 署名を Rust FFI で生成
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cert_rust import signer  # pyo3 拡張モジュール
from .loader import get_private_key_hex


def sign_with_cert(message: str, pem_path: str) -> bytes:
    """
    Dilithium 秘密鍵でメッセージを署名し、バイト列を返す
    """
    priv_hex = get_private_key_hex(pem_path)
    return signer.dilithium_sign_stub(message, priv_hex)
