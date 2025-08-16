# CA/cert_issuer.py

import os,sys
import uuid
from datetime import datetime, timedelta
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from .ca_signer import sign_certificate

def issue_client_certificate(
    user_id: str,
    ntru_public_key_hex: str,
    dilithium_public_key_hex: str,
    validity_days: int = 365
) -> dict:
    """
    クライアント証明書 (JSON 形式) を組み立て、CA 署名を付与して返す。

    Fields:
      - uuid
      - public_key             (NTRU 公開鍵の hex)
      - dilithium_public_key   (Dilithium 公開鍵の hex)
      - algorithm              ("NTRU+Dilithium")
      - issuer                 (CA 名)
      - serial_number          (UUID 文字列)
      - valid_from, valid_to   (ISO8601 UTC)
      - revoked                (bool)
      - signature              (CA による署名 hex)
      - signed_at              (ISO8601 UTC)
    """
    now = datetime.utcnow()
    cert = {
        "uuid":                 user_id,
        "public_key":           ntru_public_key_hex,
        "dilithium_public_key": dilithium_public_key_hex,
        "algorithm":            "NTRU+Dilithium",
        "issuer":               "ExampleCA",
        "serial_number":        uuid.uuid4().hex,
        "valid_from":           now.isoformat() + "Z",
        "valid_to":             (now + timedelta(days=validity_days)).isoformat() + "Z",
        "revoked":              False
    }

    # CA 署名を付与
    signed_cert = sign_certificate(cert)
    return signed_cert

if __name__ == "__main__":
    # サンプル実行: 出力イメージ確認用
    sample = issue_client_certificate(
        user_id="sample-uuid-1234",
        ntru_public_key_hex="deadbeef",
        dilithium_public_key_hex="cafebabe"
    )
    print(json.dumps(sample, indent=2, ensure_ascii=False))
