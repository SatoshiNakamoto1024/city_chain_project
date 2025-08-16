# auth_py/client_cert/dilithium_verify.py
import base64
from asn1crypto import pem, x509, core

# Dilithium Rust ラッパ
import sys, os
sys.path += [
    r"D:\city_chain_project\ntru\ntru-py",
    r"D:\city_chain_project\ntru\dilithium-py"
]
from app_dilithium import verify_message

OID_DIL_SIG_ALG = '1.3.6.1.4.1.99999.1.100'
OID_DIL_PUB_EXT = '1.3.6.1.4.1.99999.1.2'


def _pem_to_der(pem_bytes: bytes) -> bytes:
    """PEM → 純 DER"""
    if pem.detect(pem_bytes):
        _, _, der_bytes = pem.unarmor(pem_bytes)
        return der_bytes
    else:
        return pem_bytes


def extract_dilithium_ext(pem_bytes: bytes) -> bytes:
    der = _pem_to_der(pem_bytes)
    cert = x509.Certificate.load(der)
    tbs = cert['tbs_certificate']
    # asn1crypto が自動で EXPLICIT[3] を外してくれます
    exts = tbs['extensions']
    for ext in exts:
        if ext['extn_id'].dotted == OID_DIL_PUB_EXT:
            # OctetString の中身（バイト列）を native で取り出す
            return ext['extn_value'].native
    raise ValueError(f"Dilithium 拡張 {OID_DIL_PUB_EXT} が見つかりません")


def verify_pem(pem_bytes: bytes) -> bool:
    der = _pem_to_der(pem_bytes)
    cert = x509.Certificate.load(der)

    # 署名アルゴリズムチェック
    sig_algo = cert['signature_algorithm']['algorithm'].dotted
    if sig_algo != OID_DIL_SIG_ALG:
        return False

    # 公開鍵拡張取り出し
    pub = extract_dilithium_ext(pem_bytes)

    # TBSCertificate DER を再エンコードして署名検証
    tbs_der = tbs = cert['tbs_certificate'].dump()
    sig = cert['signature_value'].native
    return verify_message(tbs_der, sig, pub)
