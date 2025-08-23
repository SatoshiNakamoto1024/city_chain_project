# sending_DAG/python_sending/cert_python/cert_validator.py
"""
署名検証を Rust FFI で実行
"""
import base64
from cert_rust import verifier  # pyo3 拡張モジュール
from .loader import get_public_key_hex


def verify_signature_with_cert(
    message: str,
    b64_sig: str,
    pem_path: str
) -> bool:
    """
    Base64 署名を検証し、正当なら True。
    """
    pub_hex = get_public_key_hex(pem_path)
    sig = base64.b64decode(b64_sig.encode())
    return verifier.dilithium_verify_stub(message, sig, pub_hex)
