"""
auth_py/client_cert/dilithium_verify.py
---------------------------------------
・クライアント証明書 (PEM) から NTRU / Dilithium 公開鍵を抽出
・ルート CA の Dilithium 公開鍵で署名検証
"""

from __future__ import annotations
import base64
import sys
from pathlib import Path
from typing import Optional

# ── pyasn1 & rfc5280 ────────────────────────────────────────────
sys.path.insert(0, r"D:\city_chain_project\CA\pyasn1-master")
from pyasn1.codec.der import encoder, decoder
sys.path.insert(0, r"D:\city_chain_project\CA\pyasn1-modules-master")
from pyasn1_modules import rfc5280
from pyasn1.type import univ

# ── PQC ラッパ ─────────────────────────────────────────────────
sys.path += [
    r"D:\city_chain_project\ntru\ntru-py",
    r"D:\city_chain_project\ntru\dilithium-py",
]
from app_dilithium import verify_message  # (msg, sig, pub) -> bool

# ── カスタム OID ───────────────────────────────────────────────
OID_NTRU_ALG    = "1.3.6.1.4.1.99999.1.0"
OID_DIL_SIG_ALG = "1.3.6.1.4.1.99999.1.100"

# ───────────────────────────────────────────────────────────────
# 基本ヘルパ
# ───────────────────────────────────────────────────────────────
def _pem_to_der(pem_bytes: bytes) -> bytes:
    """-----BEGIN/END----- 行を取り除き Base64‑decode"""
    b64 = b"".join(line for line in pem_bytes.splitlines()
                   if line and line[:5] != b"-----")
    return base64.b64decode(b64)

def _parse_cert(pem_bytes: bytes) -> rfc5280.Certificate:
    """PEM → pyasn1 rfc5280.Certificate"""
    der = _pem_to_der(pem_bytes)
    cert, _ = decoder.decode(der, asn1Spec=rfc5280.Certificate())
    return cert

# ───────────────────────────────────────────────────────────────
# 公開鍵抽出
# ───────────────────────────────────────────────────────────────
def extract_ntru_pub_from_spki(pem_bytes: bytes) -> bytes:
    cert = _parse_cert(pem_bytes)
    spki = cert['tbsCertificate']['subjectPublicKeyInfo']

    if str(spki['algorithm']['algorithm']) != OID_NTRU_ALG:
        raise ValueError("algorithm OID が NTRU ではありません")

    return spki['subjectPublicKey'].asOctets()


def extract_dilithium_pub_from_spki(pem_bytes: bytes) -> Optional[bytes]:
    """
    SPKI.algorithm.parameters (= OctetString) に埋め込んだ
    Dilithium 公開鍵を取り出す。存在しなければ None。
    """
    cert = _parse_cert(pem_bytes)
    alg  = cert['tbsCertificate']['subjectPublicKeyInfo']['algorithm']

    params_any = alg.getComponentByName('parameters')
    if not (params_any and params_any.isValue):
        return None

    # ANY = OctetString(DER) として格納している
    der_octet = bytes(params_any)              # そのまま DER
    octet, _  = decoder.decode(der_octet, asn1Spec=univ.OctetString())
    return octet.asOctets()

# ───────────────────────────────────────────────────────────────
# ルート CA の Dilithium 公開鍵を 1 回だけロード
# ───────────────────────────────────────────────────────────────
def _load_ca_dilithium_pub() -> bytes:
    ca_cert_dir = Path(__file__).resolve().parents[3] / "CA" / "certs"
    ca_pem_path = max(ca_cert_dir.glob("ca_root_*.pem"))   # 最も新しいもの

    ca_pem_bytes = ca_pem_path.read_bytes()
    dil_pub = extract_dilithium_pub_from_spki(ca_pem_bytes)
    if dil_pub is None:
        raise RuntimeError("CA ルート証明書に Dilithium 公開鍵が含まれていません")
    return dil_pub

CA_DIL_PUB: bytes = _load_ca_dilithium_pub()

# ───────────────────────────────────────────────────────────────
# 署名検証
# ───────────────────────────────────────────────────────────────
def verify_pem(pem_bytes: bytes) -> bool:
    cert = _parse_cert(pem_bytes)

    if str(cert['signatureAlgorithm']['algorithm']) != OID_DIL_SIG_ALG:
        return False

    # TBSCertificate を DER 化
    tbs_der = encoder.encode(cert['tbsCertificate'])
    sig     = cert['signature'].asOctets()

    # ルート CA の Dilithium 公開鍵で検証
    return verify_message(tbs_der, sig, CA_DIL_PUB)
