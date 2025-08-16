# CA/ca_generate_cert_asn1.py

"""
本番用ルートCA PEM 発行モジュール
  ・NTRU公開鍵は SubjectPublicKeyInfo に格納
  ・Dilithium-5 で自己署名
  ・SPKI の AlgorithmIdentifier.parameters に Dilithium 公開鍵を格納
  ・拡張領域にも NTRU/Dilithium 公開鍵を追加（必要に応じて）
"""

import sys
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone

# pyasn1 のローカルモジュール読み込み
sys.path.insert(0, r"D:\city_chain_project\CA\pyasn1-master")
from pyasn1.type     import univ, char, tag, useful
from pyasn1.codec.der import encoder
from pyasn1.codec.der import encoder as _der_encoder
sys.path.insert(0, r"D:\city_chain_project\CA\pyasn1-modules-master")
from pyasn1_modules import rfc5280

# PQC ラッパーのパス
sys.path += [
    r"D:\city_chain_project\ntru\ntru-py",
    r"D:\city_chain_project\ntru\dilithium-py"
]
from ntru_encryption import NtruEncryption
from app_dilithium   import create_keypair as dil_keypair, sign_message

# OID定義
OID_NTRU_ALG     = univ.ObjectIdentifier("1.3.6.1.4.1.99999.1.0")
OID_DIL_SIG_ALG  = univ.ObjectIdentifier("1.3.6.1.4.1.99999.1.100")
OID_NTRU_PUB_EXT = univ.ObjectIdentifier("1.3.6.1.4.1.99999.1.1")
OID_DIL_PUB_EXT  = univ.ObjectIdentifier("1.3.6.1.4.1.99999.1.2")

# 保存先ディレクトリ
BASE     = Path(__file__).parent
CERT_DIR = BASE / "certs";    CERT_DIR.mkdir(exist_ok=True)
KEY_DIR  = BASE / "keys";     KEY_DIR.mkdir(exist_ok=True)
META_DIR = BASE / "metadata"; META_DIR.mkdir(exist_ok=True)

def bitstring(b: bytes) -> univ.BitString:
    return univ.BitString.fromOctetString(b)

def build_name(cn: str) -> rfc5280.Name:
    atv = rfc5280.AttributeTypeAndValue()
    atv["type"]  = rfc5280.id_at_commonName
    atv["value"] = char.UTF8String(cn)
    rdn = rfc5280.RelativeDistinguishedName(); rdn[0] = atv
    seq = rfc5280.RDNSequence(); seq[0] = rdn
    name = rfc5280.Name(); name.setComponentByName("rdnSequence", seq)
    return name

def generate_root_cert(force: bool = False) -> Path:
    # 既存ファイルがあれば使う
    existing = sorted(CERT_DIR.glob("ca_root_*.pem"))
    if existing and not force:
        return existing[-1]

    # --- 1. 鍵ペア生成 ---
    ntru = NtruEncryption()
    kp = ntru.generate_keypair()
    ntru_pub, ntru_priv = bytes(kp["public_key"]), bytes(kp["secret_key"])
    dil_pub,  dil_priv  = map(bytes, dil_keypair())

    # --- 2. SPKI & TBSCertificate 組み立て ---
    now = datetime.now(timezone.utc)

    # SubjectPublicKeyInfo: NTRU 公開鍵 + parameters に Dilithium 公開鍵
    spki = rfc5280.SubjectPublicKeyInfo()
    spki["algorithm"]["algorithm"]  = OID_NTRU_ALG
    # ← ここで AlgorithmIdentifier.parameters に Dilithium 鍵を入れる
    spki["algorithm"]["parameters"] = univ.Any(
        encoder.encode(univ.OctetString(dil_pub))
    )
    spki["subjectPublicKey"]        = bitstring(ntru_pub)

    tbs = rfc5280.TBSCertificate()
    tbs["version"]                = 2
    tbs["serialNumber"]           = int(uuid.uuid4())
    tbs["signature"]["algorithm"] = OID_DIL_SIG_ALG
    tbs["issuer"]                 = build_name("MyProductionCA")
    tbs["subject"]                = tbs["issuer"]

    validity = rfc5280.Validity()
    validity["notBefore"]["utcTime"] = useful.UTCTime(now.strftime("%y%m%d%H%M%SZ"))
    validity["notAfter"]["utcTime"]  = useful.UTCTime(
        (now + timedelta(days=3650)).strftime("%y%m%d%H%M%SZ")
    )
    tbs["validity"]             = validity
    tbs["subjectPublicKeyInfo"] = spki

    # --- 3. 拡張領域に NTRU/Dilithium 公開鍵を追加（オプション） ---
    exts = rfc5280.Extensions()
    for idx, (oid, val) in enumerate([
        (OID_NTRU_PUB_EXT, ntru_pub),
        (OID_DIL_PUB_EXT,  dil_pub)
    ]):
        ext = rfc5280.Extension()
        ext["extnID"]    = oid
        ext["critical"]  = False
        ext["extnValue"] = encoder.encode(univ.OctetString(val))  # DER encode!
        exts[idx] = ext

    # EXPLICIT[3] タグでセット
    exts_tagged = exts.subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)
    )
    tbs.setComponentByName("extensions", exts_tagged)

    # --- 4. DER 化 & Dilithium 署名 ---
    tbs_der = encoder.encode(tbs)
    sig     = sign_message(tbs_der, dil_priv)

    cert = rfc5280.Certificate()
    cert["tbsCertificate"]               = tbs
    cert["signatureAlgorithm"]["algorithm"] = OID_DIL_SIG_ALG
    cert["signature"]                     = bitstring(sig)

    # --- 5. PEM 化 & ファイル保存 ---
    cert_der = encoder.encode(cert)
    cert_pem = (
        b"-----BEGIN CERTIFICATE-----\n" +
        base64.encodebytes(cert_der) +
        b"-----END CERTIFICATE-----\n"
    )

    ts = now.strftime("%Y%m%dT%H%M%SZ")
    out_pem = CERT_DIR / f"ca_root_{ts}.pem"
    out_pem.write_bytes(cert_pem)
    (KEY_DIR / "ca_ntru_private.bin").write_bytes(ntru_priv)
    (KEY_DIR / "ca_dilithium_private.bin").write_bytes(dil_priv)

    META_DIR.joinpath(f"ca_root_{ts}.json").write_text(
        json.dumps({
            "created": ts,
            "pem_path": str(out_pem),
            "ntru_public_b64":      base64.b64encode(ntru_pub).decode(),
            "dilithium_public_hex": dil_pub.hex()
        }, indent=2),
        encoding="utf-8"
    )

    return out_pem

if __name__ == "__main__":
    path = generate_root_cert(force=True)
    print(f"[OK] Root CA PEM → {path}")
