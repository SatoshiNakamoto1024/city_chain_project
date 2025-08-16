# network/DAGs/common/security/certs.py
"""
certs.py
X.509 PEM 証明書のロード・CN 取得・チェーン検証
"""
from typing import List
from cryptography import x509
from cryptography.hazmat.backends import default_backend


def load_pem_cert(path: str) -> x509.Certificate:
    """
    PEM 形式の X.509 証明書を読み込んで返す。
    """
    data = open(path, "rb").read()
    return x509.load_pem_x509_certificate(data, default_backend())


def get_cn(cert: x509.Certificate) -> str:
    """
    証明書の Subject Common Name を返す。
    """
    from cryptography.x509.oid import NameOID
    for attr in cert.subject:
        if attr.oid == NameOID.COMMON_NAME:
            return attr.value
    raise ValueError("証明書に CN フィールドがありません")


def validate_chain(
    cert: x509.Certificate,
    trust_anchors: List[x509.Certificate],
) -> bool:
    """
    cert の Issuer が trust_anchors のいずれかと一致すれば True。
    簡易チェーン検証。
    """
    issuer = cert.issuer
    return any(anchor.subject == issuer for anchor in trust_anchors)
