# auth_py/revoke_cert_service.py

import boto3
from datetime import datetime, timezone
from login_app.config import DYNAMODB_TABLE

dynamodb = boto3.resource("dynamodb")
users_table = dynamodb.Table(DYNAMODB_TABLE)

def revoke_certificate_by_uuid(user_uuid: str):
    now_iso = datetime.now(timezone.utc).isoformat()

    response = users_table.update_item(
        Key={"uuid": user_uuid, "session_id": "REGISTRATION"},
        UpdateExpression="SET certificate.revoked = :r, certificate.revoked_at = :t",
        ExpressionAttributeValues={
            ":r": True,
            ":t": now_iso
        },
        ReturnValues="UPDATED_NEW"
    )
    return response
