# network/DAGs/common/security/signing.py
"""
signing.py
Dilithium5・NTRU・RSA 各署名・検証・鍵生成を一元公開
"""
import os
import sys

# ─── Dilithium5 ───
from dilithium5 import (
    generate_keypair as _dilithium_generate,
    sign as _dilithium_sign,
    verify as _dilithium_verify,
)

def create_dilithium_keypair() -> tuple[bytes, bytes]:
    """
    Rust バインディングの dilithium5.generate_keypair() を呼び、
    (public_key, secret_key) を返す。
    """
    return _dilithium_generate()

def sign_dilithium(message: bytes, secret_key: bytes) -> bytes:
    """
    Dilithium5 で署名 → SignedMessage bytes
    """
    return _dilithium_sign(message, secret_key)

def verify_dilithium(message: bytes, signed_message: bytes, public_key: bytes) -> bool:
    """
    Dilithium5 で検証 → True/False
    """
    return _dilithium_verify(message, signed_message, public_key)


# ─── NTRU ───
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\ntru-py"))
from ntru_encryption import NtruEncryption
_ntru = NtruEncryption()

def create_ntru_keypair() -> tuple[bytes, bytes]:
    """
    NTRU で鍵ペア生成 → {"public_key", "secret_key"} から取り出して返却
    """
    kp = _ntru.generate_keypair()
    return kp["public_key"], kp["secret_key"]

def encrypt_ntru(public_key: bytes) -> tuple[bytes, bytes]:
    """
    NTRU で暗号化 → (cipher_text, shared_secret)
    """
    return _ntru.encrypt(public_key)

def decrypt_ntru(cipher_text: bytes, secret_key: bytes) -> bytes:
    """
    NTRU で復号 → shared_secret
    """
    return _ntru.decrypt(cipher_text, secret_key)


# ─── RSA ───
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\rsa-sign-py"))
from rsa_sign import (
    generate_keypair as _rsa_generate,
    sign_message as _rsa_sign,
    verify_signature as _rsa_verify,
)

def create_rsa_keypair(key_size: int = 2048):
    """
    RSA 鍵ペア生成 → (private_key_obj, public_key_obj)
    """
    return _rsa_generate(key_size)

def sign_rsa(message: bytes, private_key) -> bytes:
    """
    RSA 署名 → base64‐文字列をバイト化して返す
    """
    # rsa_sign.sign_message は str を返すので .encode() する
    return _rsa_sign(private_key, message.decode()).encode()

def verify_rsa(message: bytes, signature: bytes, public_key) -> bool:
    """
    RSA 検証
    """
    return _rsa_verify(public_key, message.decode(), signature.decode())
