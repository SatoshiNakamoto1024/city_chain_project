# CA/ca_generate_cert.py  ★全文差し替え
"""
NTRU 公開鍵 + Dilithium5 署名で自己署名 CA 証明書 (X.509/PEM) を生成する。
"""

import os, sys, json, uuid, base64
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID, ObjectIdentifier
from cryptography.hazmat.backends import default_backend

# ------------------------------------------------------------
# PQC ライブラリ
# ------------------------------------------------------------
sys.path.append(r"D:\city_chain_project\ntru\ntru-py")
sys.path.append(r"D:\city_chain_project\ntru\dilithium-py")

from ntru_encryption import NtruEncryption                 # ← クラス
from app_dilithium  import create_keypair as dil_keypair   # ← ★ここを修正
from app_dilithium  import sign_message

# ------------------------------------------------------------
# OID 定義（プライベート OID 例）
# ------------------------------------------------------------
NTRU_ALG_OID      = ObjectIdentifier("1.3.6.1.4.1.99999.1.0")
NTRU_EXT_OID      = ObjectIdentifier("1.3.6.1.4.1.99999.1.1")
DIL_PUB_EXT_OID   = ObjectIdentifier("1.3.6.1.4.1.99999.1.2")
DIL_SIG_ALG_OID   = ObjectIdentifier("1.3.6.1.4.1.99999.1.100")

# ------------------------------------------------------------
# 保存ディレクトリ
# ------------------------------------------------------------
CA_DIR   = Path(r"D:\city_chain_project\CA")
KEY_DIR  = CA_DIR / "keys"
CERT_DIR = CA_DIR / "certs"
META_DIR = CA_DIR / "metadata"
for d in (KEY_DIR, CERT_DIR, META_DIR):
    d.mkdir(parents=True, exist_ok=True)

def _save(path: Path, data: bytes):
    with open(path, "wb") as f:
        f.write(data)

# ------------------------------------------------------------
# メイン
# ------------------------------------------------------------
def main():
    # ① NTRU & Dilithium5 キー生成 -----------------------------
    ntru    = NtruEncryption()
    ntru_kp = ntru.generate_keypair()
    ntru_pub, ntru_priv = ntru_kp["public_key"], ntru_kp["secret_key"]

    dil_pub, dil_priv   = dil_keypair()

    # ② TBSCertificate 構築 -----------------------------------
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Example-Quantum-CA")])
    now  = datetime.now(timezone.utc)

    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(
            x509.PublicKeyInfo(
                algorithm=NTRU_ALG_OID,
                public_bytes=ntru_pub
            )
        )
        .serial_number(int(uuid.uuid4()))
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.UnrecognizedExtension(NTRU_EXT_OID, ntru_pub), critical=False)
        .add_extension(x509.UnrecognizedExtension(DIL_PUB_EXT_OID, dil_pub), critical=False)
    )
    tbs_cert = builder._build(default_backend())

    # ③ Dilithium 署名 ----------------------------------------
    tbs_der = tbs_cert.public_bytes(serialization.Encoding.DER)
    dil_sig = sign_message(tbs_der, dil_priv)

    ca_cert = x509.Certificate(
        tbs_cert.tbs_certificate_bytes,
        DIL_SIG_ALG_OID,
        dil_sig,
        tbs_cert._backend,
    )

    # ④ 保存 --------------------------------------------------
    pem_bytes = ca_cert.public_bytes(serialization.Encoding.PEM)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    cert_path = CERT_DIR / f"ca_root_{ts}.pem"
    _save(cert_path, pem_bytes)

    _save(KEY_DIR / "ca_ntru_private.bin", ntru_priv)
    _save(KEY_DIR / "ca_dilithium_private.bin", dil_priv)

    meta = {
        "created": ts,
        "cert_file": str(cert_path),
        "ntru_public": base64.b64encode(ntru_pub).decode(),
        "dilithium_public": dil_pub.hex(),
    }
    (META_DIR / f"ca_root_{ts}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    print(f"[OK] CA PEM saved → {cert_path}")

if __name__ == "__main__":
    main()
