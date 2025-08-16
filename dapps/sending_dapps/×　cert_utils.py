# sending_dapps/cert_utils.py
"""
証明書 / 署名検証ユーティリティ
"""

from __future__ import annotations
import base64, logging, sys
from pathlib import Path
from functools import lru_cache

# ─ pyasn1 --------------------------------------------------------
sys.path += [
    r"D:\city_chain_project\CA\pyasn1-master",
    r"D:\city_chain_project\CA\pyasn1-modules-master",
]
from pyasn1.codec.der import decoder, encoder
from pyasn1_modules   import rfc5280
from pyasn1.type      import univ

# ─ PQC wrapper ---------------------------------------------------
sys.path += [
    r"D:\city_chain_project\ntru\ntru-py",
    r"D:\city_chain_project\ntru\dilithium-py",
]
from app_dilithium import verify_message

# ─ Local ---------------------------------------------------------
from sending_dapps.cert_cache import cached_verify

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OID_NTRU_ALG    = "1.3.6.1.4.1.99999.1.0"
OID_DIL_SIG_ALG = "1.3.6.1.4.1.99999.1.100"

CA_PEM_PATH = max((Path(__file__).parents[2] / "CA" / "certs").glob("ca_root_20250503T080950Z.pem"))
_CA_PEM = CA_PEM_PATH.read_bytes()

def _pem_to_der(pem: bytes) -> bytes:
    return base64.b64decode(b"".join(l for l in pem.splitlines()
                                     if l and l[:5] != b"-----"))

def _parse_cert(pem: bytes):
    return decoder.decode(_pem_to_der(pem), asn1Spec=rfc5280.Certificate())[0]

@lru_cache(maxsize=1)
def _ca_dil_pub() -> bytes:
    cert = _parse_cert(_CA_PEM)
    param_any = cert["tbsCertificate"]["subjectPublicKeyInfo"]["algorithm"]["parameters"]
    octet, _  = decoder.decode(bytes(param_any), asn1Spec=univ.OctetString())
    return bytes(octet)

# ──────────────────────────────────────────────────────────
@cached_verify
def verify_client_certificate(pem: bytes) -> bool:
    """重い処理を cert_cache.cached_verify でメモ化"""
    try:
        cert = _parse_cert(pem)
        if str(cert["signatureAlgorithm"]["algorithm"]) != OID_DIL_SIG_ALG:
            return False
        tbs_der = encoder.encode(cert["tbsCertificate"])
        sig     = cert["signature"].asOctets()
        return verify_message(tbs_der, sig, _ca_dil_pub())
    except Exception as e:
        logger.warning("cert verify exception: %s", e)
        return False

def verify_message_signature(msg: bytes, sig: bytes, pub: bytes) -> bool:
    try:
        return verify_message(msg, sig, pub)
    except Exception as e:
        logger.warning("sig verify exception: %s", e)
        return False
