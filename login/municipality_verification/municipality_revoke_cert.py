# municipality_verification/municipality_revoke_cert.py

import os
import datetime
import logging
import boto3

# 環境変数から UsersTable を取得
AWS_REGION  = os.getenv("AWS_REGION", "us-east-1")
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")

dynamodb    = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USERS_TABLE)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def municipality_revoke_cert(user_uuid: str,
                             performed_by: str,
                             tenant_id: str):
    """
    ユーザーの証明書を失効するロジック例
    - user_uuid: 失効対象ユーザーの UUID
    - performed_by: 承認操作を行う職員の staff_id
    - tenant_id: 認可用テナント ID（municipality）
    """
    # 1) 該当ユーザーを取得（session_id="REGISTRATION" をキーに含む）
    user = users_table.get_item(
        Key={"uuid": user_uuid, "session_id": "REGISTRATION"}
    ).get("Item")

    if not user:
        return {"error": "User not found"}, 404

    # 2) tenant_id（市町村）が一致するかチェック
    if user.get("tenant_id") != tenant_id:
        return {"error": "Unauthorized tenant access"}, 403

    # 3) すでに revoked == True なら何もしない
    if user.get("certificate", {}).get("revoked") is True:
        logger.info("CERT_ALREADY_REVOKED uuid=%s by=%s", user_uuid, performed_by)
        return {"message": "Already revoked"}, 200

    # 4) DynamoDB 更新して revoked フラグと revoked_at をセット
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    users_table.update_item(
        Key={"uuid": user_uuid, "session_id": "REGISTRATION"},
        UpdateExpression="SET certificate.revoked = :r, certificate.revoked_at = :t",
        ExpressionAttributeValues={":r": True, ":t": ts},
    )
    logger.info("CERT_REVOKED_MUNICIPAL uuid=%s by=%s", user_uuid, performed_by)
    return {"success": True, "revoked_at": ts}
