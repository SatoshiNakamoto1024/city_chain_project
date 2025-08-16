# CA/client_cert_utils.py

import base64
from pathlib import Path

from pyasn1.codec.der import decoder
from pyasn1_modules import rfc5280
from pyasn1.type import univ    # 追加

def extract_keys_from_pem(pem_path: str) -> tuple[bytes, bytes]:
    p = Path(pem_path)
    if not p.exists():
        raise FileNotFoundError(f"PEM ファイルが見つかりません: {pem_path}")

    # 1) PEM → DER
    lines = p.read_text(encoding="utf-8").splitlines()
    b64_lines = [line for line in lines if line and not line.startswith("-----")]
    der_bytes = base64.b64decode("".join(b64_lines))

    # 2) ASN.1 デコード → rfc5280.Certificate
    cert, _ = decoder.decode(der_bytes, asn1Spec=rfc5280.Certificate())
    tbs = cert["tbsCertificate"]

    # 3) SubjectPublicKeyInfo を取り出す
    spki = tbs.getComponentByName("subjectPublicKeyInfo")

    # 3-1) NTRU 公開鍵（BIT STRING のバイナリそのまま）
    ntru_pub_bs = spki.getComponentByName("subjectPublicKey").asOctets()
    ntru_pub = bytes(ntru_pub_bs)

    # 3-2) Dilithium 公開鍵（algorithm.parameters に埋まっている OCTET STRING）
    alg = spki.getComponentByName("algorithm")
    params_any = alg.getComponentByName("parameters")
    if not (params_any and params_any.isValue):
        raise ValueError("SPKI.algorithm.parameters に Dilithium 公開鍵が含まれていません")

    # ここで params_any は「DER エンコードされた OctetString」のバイト列なので、一段階デコード
    der_octet = bytes(params_any)             # DER エンコードされた OCTET STRING
    octet, _ = decoder.decode(der_octet, asn1Spec=univ.OctetString())  # ← univ.OctetString() を使う
    dilithium_pub = bytes(octet.asOctets())

    return ntru_pub, dilithium_pub
