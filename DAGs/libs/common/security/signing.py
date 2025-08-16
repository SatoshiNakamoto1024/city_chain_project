# network/DAGs/common/security/signing.py
"""
signing.py
==========

* Dilithium5（Rust FFI 経由）
* NTRU-KEM     （Rust FFI 経由）
* RSA-PKCS#1 v1.5（Rust FFI 経由）

――― を 1 つの API で提供する高水準ラッパー。

すべて **bytes 入出力** を保証しているため、上位レイヤは実装差異を意識せずに利用できます。
"""

from __future__ import annotations
import base64
import os
import sys
from typing import Tuple

# ──────────────────────────────────────────────
# Dilithium5 bindings  (ntru/dilithium-py)
# ──────────────────────────────────────────────
try:
    # “pip install dilithium5” でインストール済み想定
    from app_dilithium import (
        create_keypair as _dl_keypair,
        sign_message as _dl_sign,
        verify_message as _dl_verify,
    )
except ImportError:
    # リポジトリ直下から相対 import したい場合
    _DILITHIUM_PY = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 "../../../..",
                                                 "ntru", "dilithium-py"))
    sys.path.append(_DILITHIUM_PY)
    from app_dilithium import (
        create_keypair as _dl_keypair,
        sign_message as _dl_sign,
        verify_message as _dl_verify,
    )

# ──────────────────────────────────────────────
# NTRU-KEM bindings  (ntru/ntru-py)
# ──────────────────────────────────────────────
try:
    from ntru_encryption import NtruEncryption
except ImportError:
    _NTRU_PY = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "../../../..",
                                            "ntru", "ntru-py"))
    sys.path.append(_NTRU_PY)
    from ntru_encryption import NtruEncryption

_ntru = NtruEncryption()

# ──────────────────────────────────────────────
# RSA bindings  (ntru/rsa-sign-py)
# ──────────────────────────────────────────────
try:
    from rsa_sign import (
        generate_keypair as _rsa_keypair,
        sign_message as _rsa_sign,
        verify_signature as _rsa_verify,
    )
except ImportError:
    _RSA_PY = os.path.abspath("D:/city_chain_project/ntru/rsa-sign-py")
    sys.path.append(_RSA_PY)
    from rsa_sign import (
        generate_keypair as _rsa_keypair,
        sign_message as _rsa_sign,
        verify_signature as _rsa_verify,
    )

# ──────────────────────────────────────────────
# 共通ユーティリティ
# ──────────────────────────────────────────────
def _as_bytes(obj: bytes | bytearray | list[int]) -> bytes:
    """
    dilithium-py が list[int] を返すケースがあるので Bytes に統一する。
    """
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj)
    if isinstance(obj, list):
        return bytes(obj)
    raise TypeError(f"unsupported type: {type(obj)}")


# ──────────────────────────────────────────────
# Dilithium5 – API
# ──────────────────────────────────────────────
def create_dilithium_keypair() -> Tuple[bytes, bytes]:
    """(public_key, secret_key) を bytes で返す"""
    pub, sec = _dl_keypair()
    return _as_bytes(pub), _as_bytes(sec)


def sign_dilithium(message: bytes, secret_key: bytes | list[int]) -> bytes:
    """署名付きメッセージ (SignedMessage bytes) を返す"""
    sig = _dl_sign(message, _as_bytes(secret_key))
    return _as_bytes(sig)


def verify_dilithium(
    message: bytes,
    signed_message: bytes | list[int],
    public_key: bytes | list[int],
) -> bool:
    """署名検証 True/False"""
    return _dl_verify(message, _as_bytes(signed_message), _as_bytes(public_key))


# ──────────────────────────────────────────────
# NTRU-KEM – API
# ──────────────────────────────────────────────
def create_ntru_keypair() -> Tuple[bytes, bytes]:
    """(public_key, secret_key) bytes"""
    kp = _ntru.generate_keypair()
    return kp["public_key"], kp["secret_key"]


def encrypt_ntru(public_key: bytes) -> Tuple[bytes, bytes]:
    """(cipher_text, shared_secret) bytes"""
    ct, ss = _ntru.encrypt(public_key)
    return ct, ss


def decrypt_ntru(cipher_text: bytes, secret_key: bytes) -> bytes:
    """shared_secret bytes"""
    ss = _ntru.decrypt(cipher_text, secret_key)
    return ss


# ──────────────────────────────────────────────
# RSA – API
# ──────────────────────────────────────────────
def create_rsa_keypair(bits: int = 2048):
    """(private_key_obj, public_key_obj)"""
    return _rsa_keypair(bits)


def sign_rsa(message: bytes, private_key) -> bytes:
    """
    RSA-PKCS1v1.5 署名を **そのまま bytes** で返す
    （Rust 側が返す署名はすでに DER などではなく「生の 256-byte ブロック」）。
    """
    return _rsa_sign(private_key, message.decode())


def verify_rsa(message: bytes, signature: bytes | str, public_key) -> bool:
    """
    署名検証
    * bytes が渡されたらそのまま
    * str の場合は Base64 とみなして decode
    （利便性のため両方受け付ける）
    """
    if isinstance(signature, (bytes, bytearray)):
        sig_raw = signature
    else:  # str → base64
        sig_raw = base64.b64decode(signature)
    return _rsa_verify(public_key, message.decode(), sig_raw)


# ──────────────────────────────────────────────
# 公開エクスポート
# ──────────────────────────────────────────────
__all__ = [
    # Dilithium
    "create_dilithium_keypair",
    "sign_dilithium",
    "verify_dilithium",
    # NTRU
    "create_ntru_keypair",
    "encrypt_ntru",
    "decrypt_ntru",
    # RSA
    "create_rsa_keypair",
    "sign_rsa",
    "verify_rsa",
]
