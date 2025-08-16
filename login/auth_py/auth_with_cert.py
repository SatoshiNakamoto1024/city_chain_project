# login/auth_py/auth_with_cert.py
"""
auth_with_cert.py
─────────────────
PEM 証明書 → Finger-Print 変換だけに特化した薄いラッパー。
他モジュールが import ループを起こさないよう、ここは util 的に分離。
"""
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_py.client_cert_handler import pem_fingerprint

__all__ = ["cert_pem_to_fingerprint"]


def cert_pem_to_fingerprint(pem_or_fp: str) -> str:
    """
    引数が 64 桁 hex なら finger-print とみなしそのまま返す。
    それ以外は PEM とみなして finger-print を計算して返す。
    """
    if len(pem_or_fp) == 64 and all(c in "0123456789abcdef" for c in pem_or_fp.lower()):
        return pem_or_fp.lower()

    # PEM とみなして変換
    return pem_fingerprint(pem_or_fp)
