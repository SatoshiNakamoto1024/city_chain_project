import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import hashlib
import uuid
from datetime import datetime, timedelta
from CA.config import CA_NAME, DEFAULT_VALIDITY_DAYS

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from app_dilithium import create_keypair

def issue_certificate(uuid_val: str, validity_days: int = None) -> tuple[bytes, str]:
    """
    CA として証明書を発行する。
    証明書には以下の情報を含む：
      - uuid
      - 公開鍵、秘密鍵、アルゴリズム ("dilithium")
      - 発行者（issuer）： CA_NAME
      - シリアル番号（ランダムな UUID）
      - 有効期限 (valid_from, valid_to)
      - リボーク状態（初期値 False）およびリボーク日時（None）
      - CA 署名（ここでは "CA_SIGNATURE_PRODUCTION_DUMMY"、実際は HSM で署名）
    
    証明書データを JSON 化（sort_keys=True）して bytes 化し、その SHA256 ハッシュを
    フィンガープリントとして算出する。
    
    Returns:
        tuple: (cert_bytes, fingerprint)
          - cert_bytes: 証明書の JSON データ（bytes）
          - fingerprint: SHA256 ハッシュ（16進文字列）
    """
    if validity_days is None:
        validity_days = DEFAULT_VALIDITY_DAYS

    # 鍵ペア生成（実際の dilithium5 を利用）
    public_key, secret_key = create_keypair()
    
    ca_signature = "CA_SIGNATURE_PRODUCTION_DUMMY"  # 実際は HSM による署名処理
    serial_number = uuid.uuid4().hex
    valid_from = datetime.utcnow()
    valid_to = valid_from + timedelta(days=validity_days)
    
    cert_data = {
        "uuid": uuid_val,
        "public_key": public_key.hex() if isinstance(public_key, bytes) else public_key,
        "secret_key": secret_key.hex() if isinstance(secret_key, bytes) else secret_key,
        "algorithm": "dilithium",
        "issuer": CA_NAME,
        "serial_number": serial_number,
        "valid_from": valid_from.isoformat() + "Z",
        "valid_to": valid_to.isoformat() + "Z",
        "revoked": False,
        "revoked_at": None,
        "ca_signature": ca_signature
    }
    
    cert_bytes = json.dumps(cert_data, sort_keys=True).encode('utf-8')
    fingerprint = hashlib.sha256(cert_bytes).hexdigest()
    return cert_bytes, fingerprint

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python cert_issuer.py <uuid>")
        sys.exit(1)
    uuid_val = sys.argv[1]
    cert_bytes, fingerprint = issue_certificate(uuid_val)
    print("Issued Certificate:")
    print(cert_bytes.decode('utf-8'))
    print("\nFingerprint:", fingerprint)
