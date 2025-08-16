import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import boto3
from datetime import datetime
import glob
from CA.config import AWS_REGION, S3_BUCKET, DYNAMODB_TABLE, LOCAL_CERT_STORAGE, LOCAL_METADATA_STORAGE

# boto3 の設定
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)
s3 = boto3.client("s3", region_name=AWS_REGION)

def revoke_certificate(uuid_val: str) -> dict:
    """
    指定された uuid の証明書を失効（revoked=True）に更新する。
    DynamoDB、S3、およびローカル保存されたファイルを更新する。
    
    Returns:
        dict: { "uuid": uuid_val, "revoked": True, "revoked_at": <timestamp> }
    """
    response = table.get_item(Key={"uuid": uuid_val, "session_id": "CLIENT_CERT"})
    item = response.get("Item")
    if not item:
        raise Exception("Certificate metadata not found")
    revoked_at = datetime.utcnow().isoformat() + "Z"
    
    # DynamoDB 更新
    table.update_item(
        Key={"uuid": uuid_val, "session_id": "CLIENT_CERT"},
        UpdateExpression="set revoked=:r, revoked_at=:t",
        ExpressionAttributeValues={":r": True, ":t": revoked_at}
    )
    
    # S3 更新
    s3_key = item["s3_key"]
    s3_response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    cert_data = json.loads(s3_response["Body"].read().decode('utf-8'))
    cert_data["revoked"] = True
    cert_data["revoked_at"] = revoked_at
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(cert_data, ensure_ascii=False, indent=4),
        ContentType="application/json"
    )
    
    # ローカル更新
    for directory in [LOCAL_METADATA_STORAGE, LOCAL_CERT_STORAGE]:
        files = glob.glob(os.path.join(directory, f"{uuid_val}_*.json"))
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = json.load(f)
            content["revoked"] = True
            content["revoked_at"] = revoked_at
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=4)
    
    return {"uuid": uuid_val, "revoked": True, "revoked_at": revoked_at}

def list_certificates() -> list:
    """
    DynamoDB のテーブルから全証明書メタデータをスキャンして返す。
    """
    response = table.scan()
    return response.get("Items", [])
