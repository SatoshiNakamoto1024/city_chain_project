# municipality_verification/admin_tools/register_admin.py

import os
import hashlib
import boto3
from datetime import datetime

# 環境変数から DynamoDB テーブル名とリージョンを取得
AWS_REGION  = os.getenv("AWS_REGION", "us-east-1")
ADMIN_TABLE = os.getenv("ADMIN_TABLE", "AdminsTable")

# DynamoDB リソース／テーブル
dynamodb   = boto3.resource("dynamodb", region_name=AWS_REGION)
table      = dynamodb.Table(ADMIN_TABLE)


def generate_salt() -> str:
    """
    16バイトのランダムソルトを生成し、16進文字列（32文字）で返す。
    """
    return os.urandom(16).hex()


def hash_password(password: str, salt: str) -> str:
    """
    SHA-256で (salt + password) をハッシュし、16進文字列で返す。
    - salt は 16進文字列（hex）を期待。
    """
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def register_admin(admin_id: str,
                   password: str,
                   name: str,
                   session_id: str) -> None:
    """
    DynamoDB の AdminsTable テーブルに「管理者」を登録する。
    - テーブルのプライマリキーは (admin_id: HASH, session_id: RANGE) を想定。
    """
    salt = generate_salt()
    password_hash = hash_password(password, salt)
    now_iso = datetime.utcnow().isoformat() + "Z"

    item = {
        "admin_id":      admin_id,
        "session_id":    session_id,
        "password_hash": password_hash,
        "salt":          salt,
        "name":          name,
        "created_at":    now_iso
    }

    try:
        table.put_item(Item=item)
        print(f"[✓] 管理者(admin) 登録完了: {admin_id}（session_id: {session_id}）")
    except Exception as e:
        print(f"[✗] 管理者(admin) 登録失敗: {e}")
