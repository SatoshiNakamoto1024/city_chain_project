import sys
import os
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from dilithium_app import create_keypair
from typing import Optional
import json
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import boto3
# client_cert/config.py 内で定義されている設定をインポート
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from client_cert.config import CA_NAME, DEFAULT_VALIDITY_DAYS, AWS_REGION, DYNAMODB_TABLE
from client_cert.table import table

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 必要に応じて INFO に変えてもOK
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# DynamoDB のリソースとテーブルオブジェクトの作成
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

def generate_client_certificate(uuid_val: str, validity_days: int = 365) -> tuple[bytes, str]:
    """
    dilithium_app.create_keypair() を呼び出して実際の鍵ペアを生成し、
    以下の情報を含むクライアント証明書の JSON データを作成する：
      - uuid
      - 公開鍵、秘密鍵、アルゴリズム ("dilithium")
      - 発行者（issuer）： CA_NAME（もしくは "MyProductionCA"）
      - シリアル番号（ランダムな UUID）
      - 有効期限 (valid_from, valid_to)
      - リボーク状態（初期値 False）およびリボーク日時（None）
      - CA 署名（ここでは "CA_SIGNATURE_PRODUCTION" としている）
    
    証明書データを JSON 化（キーをソートして安定化）して bytes 化し、
    その SHA256 ハッシュをフィンガープリントとして算出する。

    Returns:
        tuple: (cert_bytes, fingerprint)
          - cert_bytes: 証明書の JSON データ（bytes）
          - fingerprint: SHA256 ハッシュ（16進文字列）
    """
    if validity_days is None:
        validity_days = DEFAULT_VALIDITY_DAYS

    public_key, secret_key = create_keypair()
    
    # 設定ファイルで定義されている CA_NAME を使用する（なければ "MyProductionCA" にする）
    issuer = CA_NAME if CA_NAME else "MyProductionCA"
    serial_number = uuid.uuid4().hex
    # timezone-aware な日時オブジェクトを使用して、将来の互換性を確保
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
    指定された uuid の証明書を失効（revoked=True）に更新する関数です。
    DynamoDB テーブル（複合キー: "uuid" と "session_id"）の該当アイテムを更新します。
    
    Returns:
        dict: { "uuid": uuid_val, "revoked": True, "revoked_at": <timestamp> }
    """
    # timezone-aware な日時を使用
    revoked_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    # "session_id" は証明書発行時に固定値 "CLIENT_CERT" として保存している前提
    response = table.update_item(
        Key={"uuid": uuid_val, "session_id": "CLIENT_CERT"},
        UpdateExpression="set revoked=:r, revoked_at=:t",
        ExpressionAttributeValues={":r": True, ":t": revoked_at},
        ReturnValues="ALL_NEW"
    )
    print(response)
    updated_attributes = response.get("Attributes", {})
    print("Updated attributes:", updated_attributes)
    return updated_attributes  # ← ここ重要！

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python cert_issuer.py <uuid>")
        sys.exit(1)
    uuid_val = sys.argv[1]
    cert_bytes, fingerprint = generate_client_certificate(uuid_val)
    print("Issued Certificate:")
    print(cert_bytes.decode('utf-8'))
    print("\nFingerprint:", fingerprint)

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
        return item  # ← ここで取得した証明書情報を返す
    except Exception as e:
        logger.error(f"Error getting cert info: {e}")
        return None
