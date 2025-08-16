# auth_py/client_cert/client_cert.py
import sys
import os
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from app_dilithium import create_keypair
from typing import Optional
import json
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import boto3

# client_cert/config.py 内の設定値をインポート
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from client_cert.config import CA_NAME, DEFAULT_VALIDITY_DAYS, AWS_REGION, DYNAMODB_TABLE
from client_cert.table import table

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# boto3 を利用して DynamoDB のリソースを再取得（必要に応じて）
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

def generate_client_certificate(uuid_val: str, validity_days: int = 365) -> tuple[bytes, str]:
    """
    app_dilithium.create_keypair() を呼び出して鍵ペアを生成し、
    以下の情報を含むクライアント証明書の JSON を作成する：
      - uuid, public_key, secret_key, algorithm("dilithium")
      - issuer (CA_NAME または "MyProductionCA")
      - シリアル番号（ランダムな UUID）
      - 有効期間 (valid_from, valid_to)
      - revoked (初期 False) と revoked_at (初期 None)
      - CA 署名（"CA_SIGNATURE_PRODUCTION"）
    JSON 化して bytes 化し、SHA256 ハッシュをフィンガープリントとして返す。
    """
    if validity_days is None:
        validity_days = DEFAULT_VALIDITY_DAYS

    public_key, secret_key = create_keypair()
    issuer = CA_NAME if CA_NAME else "MyProductionCA"
    serial_number = uuid.uuid4().hex
    valid_from = datetime.now(timezone.utc)
    valid_to = valid_from + timedelta(days=validity_days)
    
    cert_data = {
        "uuid": uuid_val,
        "public_key": public_key.hex() if isinstance(public_key, bytes) else public_key,
        "secret_key": secret_key.hex() if isinstance(secret_key, bytes) else secret_key,
        "algorithm": "dilithium",
        "issuer": issuer,
        "serial_number": serial_number,
        "valid_from": valid_from.isoformat().replace('+00:00', 'Z'),
        "valid_to": valid_to.isoformat().replace('+00:00', 'Z'),
        "revoked": False,
        "revoked_at": None,
        "signature": "CA_SIGNATURE_PRODUCTION"
    }
    
    cert_bytes = json.dumps(cert_data, sort_keys=True).encode('utf-8')
    fingerprint = hashlib.sha256(cert_bytes).hexdigest()
    return cert_bytes, fingerprint

def revoke_certificate(uuid_val: str) -> dict:
    """
    指定 uuid の証明書を失効状態 (revoked=True) に更新する。
    更新後の属性を返す。
    """
    revoked_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    response = table.update_item(
        Key={"uuid": uuid_val, "session_id": "CLIENT_CERT"},
        UpdateExpression="set revoked=:r, revoked_at=:t",
        ExpressionAttributeValues={":r": True, ":t": revoked_at},
        ReturnValues="ALL_NEW"
    )
    updated_attributes = response.get("Attributes", {})
    return updated_attributes

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python cert_issuer.py <uuid>")
        sys.exit(1)
    uuid_val = sys.argv[1]
    cert_bytes, fingerprint = generate_client_certificate(uuid_val)
    print("Issued Certificate:")
    print(cert_bytes.decode('utf-8'))
    print("\Fingerprint:", fingerprint)

def get_dynamodb_table():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(DYNAMODB_TABLE)

def get_certificate_info(cert_uuid: str) -> Optional[dict]:
    try:
        response = table.get_item(
            Key={'uuid': cert_uuid, 'session_id': 'CLIENT_CERT'},
            ConsistentRead=True
        )
        item = response.get('Item')
        return item
    except Exception as e:
        logger.error(f"Error getting cert info: {e}")
        return None
