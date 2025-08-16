# registration/pairing_token.py
"""
ワンタイム・ペアリングトークン管理ユーティリティ
"""
import uuid
import time
import os
import sys
import boto3
from typing import Optional

# モジュールのルートを一階層上に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from registration.config import AWS_REGION, PAIRING_TOKEN_TABLE

# DynamoDB テーブルを取得
dynamodb    = boto3.resource("dynamodb", region_name=AWS_REGION)
token_table = dynamodb.Table(PAIRING_TOKEN_TABLE)

def create_pairing_token(user_id: str, ttl_sec: int = 600) -> str:
    """
    指定ユーザーIDに紐づく 10 分間有効なワンタイムトークンを発行・保存
    :param user_id: トークンを紐づけるユーザーの UUID
    :param ttl_sec: 有効期限（秒）
    :return: 発行したトークン文字列
    """
    token = uuid.uuid4().hex
    token_table.put_item(Item={
        "pairing_token": token,         # パーティションキー
        "user_id":       user_id,       # 紐づけるユーザーID
        "expires":       int(time.time()) + ttl_sec  # TTL 用属性
    })
    return token

def consume_pairing_token(token: str) -> Optional[str]:
    """
    トークンを検証して対応する user_id を返却。成功時にトークンは削除される（使い切り）。
    :param token: クライアントから送られてきたワンタイムトークン
    :return: 正常なら user_id、失効または不正なら None
    """
    resp = token_table.get_item(Key={"pairing_token": token})
    item = resp.get("Item")
    # トークンが存在せず、または有効期限切れなら None
    if not item or item.get("expires", 0) < int(time.time()):
        return None

    # 成功したら「使い切り」として削除
    token_table.delete_item(Key={"pairing_token": token})
    return item.get("user_id")


def save_pairing_token(user_id, token):
    """
    PairingTokensTable にトークンを保存
    """
    now = datetime.now(timezone.utc).isoformat()
    pairing_tokens_table.put_item(
        Item={
            "pairing_token": token,     # パーティションキー
            "user_id": user_id,
            "created_at": now
        }
    )
