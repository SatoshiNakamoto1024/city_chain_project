# CA/test_ca_extension.py
import base64
from pathlib import Path

import pytest
from pyasn1.codec.der import decoder
from pyasn1_modules import rfc5280

CA_CERT_DIR = Path(__file__).parent / "certs"
OID_DIL_PUB_EXT = '1.3.6.1.4.1.99999.1.2'


def load_latest_ca_der():
    pem_files = sorted(
        CA_CERT_DIR.glob("ca_root_*.pem"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if not pem_files:
        pytest.skip("CA/certs にルート PEM が見つかりません")
    pem = pem_files[0].read_text(encoding="utf-8")
    b64 = "".join(line for line in pem.splitlines() if "-----" not in line)
    return base64.b64decode(b64)


def test_dilithium_extension_present():
    der = load_latest_ca_der()
    cert, _ = decoder.decode(der, asn1Spec=rfc5280.Certificate())
    tbs = cert["tbsCertificate"]

    # EXPLICIT [3] のラッパーを取得
    exts_tagged = tbs.getComponentByName("extensions")
    assert exts_tagged is not None, "extensions コンポーネントが見つかりません"

    # すでに Extensions 型で decode 済みなので再 decode は不要
    # そのまま繰り返し可能
    exts = exts_tagged

    found = any(str(ext["extnID"]) == OID_DIL_PUB_EXT for ext in exts)
    assert found, f"Dilithium 公開鍵拡張 {OID_DIL_PUB_EXT} が含まれていません"