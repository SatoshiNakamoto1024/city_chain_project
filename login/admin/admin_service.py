# admin/admin_service.py
import os, json, boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

from admin.models import (
    USER_TABLE_SESSION_REG,
    USER_TABLE_SESSION_LOCK,
    AUDIT_STREAM,
)

AWS_REGION  = os.getenv("AWS_REGION", "us-east-1")
USER_TABLE  = os.getenv("DYNAMODB_TABLE", "UsersTable")

dynamodb    = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USER_TABLE)

logs_client = boto3.client("logs", region_name=AWS_REGION)
LOG_GROUP   = os.getenv("CW_LOG_GROUP", "login_admin")
LOG_STREAM  = os.getenv("CW_LOG_STREAM", AUDIT_STREAM)


def _log_admin(action: str, detail: dict):
    ts = int(datetime.utcnow().timestamp() * 1000)
    try:
        logs_client.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[{"timestamp": ts,
                        "message": json.dumps({"action": action, **detail},
                                              ensure_ascii=False)}]
        )
    except logs_client.exceptions.ResourceNotFoundException:
        # 初回はストリーム未作成なので作ってリトライしてもいい
        pass


# ────── 失効／ロック実処理 ──────
def revoke_certificate(uuid: str, by_admin: str):
    users_table.update_item(
        Key={"uuid": uuid, "session_id": USER_TABLE_SESSION_REG},
        UpdateExpression="SET certificate.revoked = :r, "
                         "certificate.revoked_at = :t",
        ExpressionAttributeValues={
            ":r": True,
            ":t": datetime.now(timezone.utc).isoformat()
        },
    )
    _log_admin("revoke_cert", {"uuid": uuid, "by": by_admin})


def lock_user(uuid: str, by_admin: str):
    users_table.put_item(Item={
        "uuid": uuid,
        "session_id": USER_TABLE_SESSION_LOCK,
        "locked_at": datetime.now(timezone.utc).isoformat(),
    })
    _log_admin("lock_user", {"uuid": uuid, "by": by_admin})


def unlock_user(uuid: str, by_admin: str):
    users_table.delete_item(
        Key={"uuid": uuid, "session_id": USER_TABLE_SESSION_LOCK}
    )
    _log_admin("unlock_user", {"uuid": uuid, "by": by_admin})


def is_locked(uuid: str) -> bool:
    return "Item" in users_table.get_item(
        Key={"uuid": uuid, "session_id": USER_TABLE_SESSION_LOCK}
    )


def fetch_audit_logs(limit: int = 100):
    try:
        out = logs_client.get_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            limit=limit, startFromHead=False,
        )
        return [json.loads(ev["message"]) for ev in out["events"]]
    except logs_client.exceptions.ResourceNotFoundException:
        return []
