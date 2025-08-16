# CA/ca_issue_client_cert.py
"""
既存の自己署名 CA PEM（ca_generate_cert.py で生成済み）と
CA の private-key（Dilithium）を使い、クライアント証明書を発行する。
* SubjectPublicKeyInfo は NTRU 公開鍵
* TBSCertificate に Dilithium5 で署名
* PEM でクライアント証明書を保存
"""

import base64
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID, ObjectIdentifier

import sys, os
sys.path.append(r"D:\city_chain_project\ntru\dilithium-py")
from app_dilithium import sign_message

# ------------------------------------------------------------------
# 事前に生成済み CA 情報をロード
# ------------------------------------------------------------------
CA_DIR  = Path(r"D:\city_chain_project\CA")
KEY_DIR = CA_DIR / "keys"
CERT_DIR = CA_DIR / "certs"

# 最新の CA PEM & 鍵を取る雑なロジック（実運用ではバージョン管理を）
ca_pem_path  = max(CERT_DIR.glob("ca_root_*.pem"))
with open(ca_pem_path, "rb") as f:
    ca_cert = x509.load_pem_x509_certificate(f.read())

dil_priv = (KEY_DIR / "ca_dilithium_private.bin").read_bytes()

# OID
DILITHIUM_SIG_OID = ObjectIdentifier("1.3.6.1.4.1.99999.1.100")
NTRU_PUB_OID      = ObjectIdentifier("1.3.6.1.4.1.99999.1.1")
DILITHIUM_PUB_OID = ObjectIdentifier("1.3.6.1.4.1.99999.1.2")

def issue_client_cert(ntru_pub: bytes, dil_pub: bytes, common_name: str) -> bytes:
    now = datetime.now(timezone.utc)

    builder = (
        x509.CertificateBuilder()
        .subject_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        )
        .issuer_name(ca_cert.subject)
        .public_key(
            x509.PublicKeyInfo(
                algorithm=x509.ObjectIdentifier("1.3.6.1.4.1.99999.1.0"),
                public_bytes=ntru_pub
            )
        )
        .serial_number(int(uuid.uuid4()))
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.UnrecognizedExtension(NTRU_PUB_OID, ntru_pub), critical=False
        )
        .add_extension(
            x509.UnrecognizedExtension(DILITHIUM_PUB_OID, dil_pub), critical=False
        )
    )

    tbs_cert = builder._build(default_backend())

    # Dilithium 署名
    tbs_der  = tbs_cert.public_bytes(serialization.Encoding.DER)
    dil_sig  = sign_message(tbs_der, dil_priv)

    client_cert = x509.Certificate(
        tbs_cert.tbs_certificate_bytes,
        DILITHIUM_SIG_OID,
        dil_sig,
        tbs_cert._backend
    )

    return client_cert.public_bytes(serialization.Encoding.PEM)

# ------------------------------------------------------------------
# CLI テスト用エントリーポイント
# ------------------------------------------------------------------
if __name__ == "__main__":
    # ダミー公開鍵を適当に生成（本来は端末側の NTRU / Dilithium 公開鍵）
    dummy_ntru_pub  = os.urandom(1024)       # ←実際は ntru_encryption.generate_keypair()[0]
    dummy_dil_pub   = os.urandom(1472)       # ←実際は dilithium_app.generate_keypair()[0]

    pem_bytes = issue_client_cert(dummy_ntru_pub, dummy_dil_pub, "demo-client-01")
    outfile   = CERT_DIR / f"client_demo_{uuid.uuid4().hex}.pem"
    outfile.write_bytes(pem_bytes)
    print(f"[OK] Client PEM saved → {outfile}")
