# login_app/login_service.py
"""
login_service.py

• UsersTable からユーザーを取得  
• パスワードとクライアント証明書フィンガープリントの検証  
"""

import os
import sys
import logging
import hmac
import boto3
from boto3.dynamodb.conditions import Key, Attr

# プロジェクトルートを import パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ---- 共通設定 ----
from login_app.config import AWS_REGION, USERS_TABLE          # DynamoDB テーブル名など
from auth_py.password_manager import hash_password  # ← これで統一 OK

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---- DynamoDB 初期化 ----
dynamodb     = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table  = dynamodb.Table(USERS_TABLE)

# =====================================================================
# 取得系ヘルパ
# =====================================================================

def get_user_by_login(login: str) -> dict | None:
    """
    username / email / uuid いずれかが一致するユーザーを返す
    （GSI を作っていない前提なので scan フォールバック）
    """
    try:
        resp = users_table.scan(
            FilterExpression=(
                "#u = :login OR #e = :login OR #id = :login"
            ),
            ExpressionAttributeNames={
                "#u":  "username",
                "#e":  "email",
                "#id": "uuid",
            },
            ExpressionAttributeValues={":login": login},
            ConsistentRead=True,
        )
        items = resp.get("Items", [])
        return items[0] if items else None
    except Exception as e:
        logger.error("get_user_by_login error: %s", e)
        return None


def get_user_by_uuid(user_uuid: str) -> dict | None:
    try:
        resp = users_table.query(
            KeyConditionExpression=Key("uuid").eq(user_uuid),
            Limit=1,
            ConsistentRead=True,
        )
        if resp.get("Items"):
            return resp["Items"][0]
    except Exception as e:
        logger.warning("query failed: %s", e)

    try:
        resp = users_table.scan(
            FilterExpression=Attr("uuid").eq(user_uuid),
            Limit=1,
            ConsistentRead=True,
        )
        return resp.get("Items", [None])[0]
    except Exception as e:
        logger.error("scan failed: %s", e)
        return None


# =====================================================================
# 検証ロジック
# =====================================================================

def verify_password(password: str, user_item: dict) -> bool:
    """
    登録済みユーザーの password_hash と一致するかチェック  
    * salt は DB では hex 文字列で保存している前提  
    * 比較は timing‑safe な hmac.compare_digest
    """
    salt_hex     = user_item.get("salt")
    stored_hash  = user_item.get("password_hash")

    if not salt_hex or not stored_hash:
        logger.error("verify_password: salt or hash missing")
        return False

    # hex → bytes へ戻す
    try:
        salt_bytes = bytes.fromhex(salt_hex)
    except ValueError:
        logger.error("verify_password: invalid salt format (%s)", salt_hex)
        return False

    calc_hash = hash_password(password, salt_bytes)
    return hmac.compare_digest(stored_hash, calc_hash)


def verify_cert_fp(client_fp: str, user_item: dict) -> bool:
    """
    クライアント証明書フィンガープリントが一致するか
    """
    return client_fp == user_item.get("client_cert_fingerprint")


__all__ = [
    "get_user_by_login",
    "get_user_by_uuid",
    "verify_password",
    "verify_cert_fp",
]
