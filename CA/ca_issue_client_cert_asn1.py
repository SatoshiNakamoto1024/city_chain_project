# CA/ca_issue_client_cert_asn1.py
"""
クライアント証明書発行モジュール（本番用）
  • SPKI に NTRU 公開鍵と Dilithium 公開鍵（parameters）を格納
  • Dilithium‐5 署名
  • pyasn1 で DER を構築
"""
import sys, uuid, base64
from pathlib import Path
from datetime import datetime, timedelta, timezone

print("[INFO] ca_issue_client_cert_asn1.py loaded")

# pyasn1 & rfc5280
sys.path.insert(0, r"D:\city_chain_project\CA\pyasn1-master")
from pyasn1.type     import univ, char, useful
from pyasn1.codec.der import encoder, decoder
from pyasn1.codec.der import encoder as _der_encoder
from pyasn1.type.univ import Any, OctetString
sys.path.insert(0, r"D:\city_chain_project\CA\pyasn1-modules-master")
from pyasn1_modules import rfc5280

# PQC ラッパー
sys.path += [
    r"D:\city_chain_project\ntru\ntru-py",
    r"D:\city_chain_project\ntru\dilithium-py"
]
from ntru_encryption import NtruEncryption
from app_dilithium   import create_keypair as dil_keypair, sign_message

# OID
OID_NTRU_ALG    = univ.ObjectIdentifier('1.3.6.1.4.1.99999.1.0')
OID_DIL_SIG_ALG = univ.ObjectIdentifier('1.3.6.1.4.1.99999.1.100')

# ディレクトリ
BASE       = Path(__file__).parent
CERT_DIR   = BASE / "certs"
KEY_DIR    = BASE / "keys"
CLIENT_DIR = BASE / "client_certs"
CLIENT_DIR.mkdir(exist_ok=True)

# ルート CA 読み込み
ca_pem = max(CERT_DIR.glob('ca_root_*.pem'))
der    = b''.join(
    base64.b64decode(l)
    for l in ca_pem.read_bytes().splitlines()
    if b'-----' not in l
)
ca_cert, _   = decoder.decode(der, asn1Spec=rfc5280.Certificate())
ca_dil_priv = (KEY_DIR / 'ca_dilithium_private.bin').read_bytes()

def bitstr(b: bytes) -> univ.BitString:
    return univ.BitString.fromOctetString(b)

def name(cn: str) -> rfc5280.Name:
    atv = rfc5280.AttributeTypeAndValue()
    atv['type']  = rfc5280.id_at_commonName
    atv['value'] = char.UTF8String(cn)
    rdn = rfc5280.RelativeDistinguishedName(); rdn[0] = atv
    seq = rfc5280.RDNSequence(); seq[0] = rdn
    nm  = rfc5280.Name(); nm.setComponentByName('rdnSequence', seq)
    return nm

def issue_client_cert(ntru_pub: bytes,
                      dil_pub:  bytes,
                      cn:       str) -> bytes:
    """クライアント証明書を DER→PEM で返す"""

    now = datetime.now(timezone.utc)

    # 1) SPKI 作成
    spki = rfc5280.SubjectPublicKeyInfo()
    # 1.1 NTRU OID
    spki['algorithm']['algorithm']  = OID_NTRU_ALG
    # 1.2 ここで Dilithium 公開鍵を埋め込む
    # ─── Dilithium 公開鍵を DER-エンコードして ANY として埋め込む ───
    spki['algorithm']['parameters'] = univ.Any(
    _der_encoder.encode(univ.OctetString(dil_pub))
    )
    # 1.3 NTRU 公開鍵本体を BIT STRING に
    spki['subjectPublicKey']        = bitstr(ntru_pub)

    # 2) TBSCertificate
    tbs = rfc5280.TBSCertificate()
    tbs['version']      = 2
    tbs['serialNumber'] = int(uuid.uuid4())
    tbs['signature']['algorithm'] = OID_DIL_SIG_ALG
    tbs['issuer']  = ca_cert['tbsCertificate']['subject']
    tbs['subject'] = name(cn)

    # 2.1 有効期間
    val = rfc5280.Validity()
    val['notBefore']['utcTime'] = useful.UTCTime(now.strftime('%y%m%d%H%M%SZ'))
    val['notAfter']['utcTime']  = useful.UTCTime((now + timedelta(days=365)).strftime('%y%m%d%H%M%SZ'))
    tbs['validity']             = val

    # 2.2 SPKI をセット
    tbs['subjectPublicKeyInfo'] = spki

    # 3) DER 化 → Dilithium 署名
    tbs_der = encoder.encode(tbs)
    sig     = sign_message(tbs_der, ca_dil_priv)

    # 4) Certificate 全体
    cert = rfc5280.Certificate()
    cert['tbsCertificate']                 = tbs
    cert['signatureAlgorithm']['algorithm'] = OID_DIL_SIG_ALG
    cert['signature']                       = bitstr(sig)

    # 5) PEM 化
    der_bytes = encoder.encode(cert)
    pem = (
        b"-----BEGIN CERTIFICATE-----\n"
        + base64.encodebytes(der_bytes)
        + b"-----END CERTIFICATE-----\n"
    )
    return pem

if __name__ == '__main__':
    # テスト用
    ntru_pub = bytes(NtruEncryption().generate_keypair()['public_key'])
    dil_pub, _ = dil_keypair()
    pem = issue_client_cert(ntru_pub, dil_pub, 'demo-client-01')
    out = CLIENT_DIR / f'client_demo_{uuid.uuid4().hex}.pem'
    out.write_bytes(pem)
    print('[OK] Client cert saved →', out)
