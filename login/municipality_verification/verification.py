# municipality_verification/verification.py

"""
ユーザー承認用 DynamoDB アクセス関数
(fill in: UsersTable に store された「保留中ユーザー」を扱う)
"""

import os
import sys
import boto3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from municipality_verification.config import AWS_REGION, USERS_TABLE

dynamodb    = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USERS_TABLE)


def get_pending_users() -> list[dict]:
    """
    UsersTable から approval_status="pending" のアイテムをすべて取得し、リストで返す。
    """
    resp = users_table.scan(
        FilterExpression="approval_status = :st",
        ExpressionAttributeValues={":st": "pending"},
    )
    return resp.get("Items", [])


def approve_user(uuid_val: str) -> None:
    """
    指定した uuid_val を持つユーザーの approval_status を "approved" に更新する。
    """
    users_table.update_item(
        Key={"uuid": uuid_val, "session_id": "REGISTRATION"},
        UpdateExpression="SET approval_status = :s",
        ExpressionAttributeValues={":s": "approved"},
    )


def reject_user(uuid_val: str) -> None:
    """
    指定した uuid_val を持つユーザーの approval_status を "rejected" に更新する。
    """
    users_table.update_item(
        Key={"uuid": uuid_val, "session_id": "REGISTRATION"},
        UpdateExpression="SET approval_status = :s",
        ExpressionAttributeValues={":s": "rejected"},
    )
