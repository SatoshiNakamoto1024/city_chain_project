# account_manager/register_account.py

"""
register_account.py
-------------------
resident / staff / admin を 1 本の窓口で登録するラッパ。

* resident → registration.register_user() を呼んで UsersTable 等に本登録
* staff   → UsersTable 登録はスキップし（既存 UI で無関係のため）、
             MunicipalStaffs に最低限のサマリ行を複製
* admin   → 同様に AdminsTable に最低限のサマリ行を複製
"""

from __future__ import annotations
import os
import sys
import copy
import logging
import boto3
import secrets
import uuid
from datetime import datetime, timezone

# registration.register_user は resident 用の既存関数
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from registration.registration import register_user

from login_app.account_manager.config import (
    AWS_REGION,
    STAFF_TABLE,
    ADMIN_TABLE,
)
from auth_py.password_manager import hash_password

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB テーブル
dynamodb  = boto3.resource("dynamodb", region_name=AWS_REGION)
staff_tbl = dynamodb.Table(STAFF_TABLE)   # MunicipalStaffs
admin_tbl = dynamodb.Table(ADMIN_TABLE)   # AdminsTable

def _generate_salt() -> str:
    """16 バイト乱数を 32 文字 hex にして返す"""
    return secrets.token_hex(16)

def _copy_to(table, item: dict[str, str]) -> None:
    """
    DynamoDB へサマリ行を書き込む際に
    * None → 空文字
    * 全フィールドを str() 化
    して型エラーを回避。
    """
    safe_item = {k: "" if v is None else str(v) for k, v in item.items()}
    try:
        table.put_item(Item=safe_item)
    except Exception as e:
        logger.warning("copy_to %s failed: %s", table.name, e)

def register_account(data: dict) -> dict:
    """
    role (resident/staff/admin) に応じて登録を振り分けるFacade。
    staff/admin は本登録を行わず、サマリだけ作成します。
    """
    role = (data.get("role") or "resident").lower()
    username = data.get("username", "")
    raw_pw = data.get("password", "")

    # 1) salt / password_hash を先に生成
    salt_hex = _generate_salt()                             # str
    pw_hash  = hash_password(raw_pw, bytes.fromhex(salt_hex))  # str

    # 2) resident の本登録 or staff/admin のダミー登録
    if role == "resident":
        # 本物のユーザー登録を呼び出し
        result = register_user(copy.deepcopy(data))
    else:
        # staff/admin は本登録不要 → 最低限のフィールドを自前で生成
        fake_uuid = str(uuid.uuid4())
        now_iso   = datetime.now(timezone.utc).isoformat()
        result = {
            "uuid":        fake_uuid,
            "created_at":  now_iso,
            "fingerprint": "",
        }

    # 3) サマリ共通項目
    summary_common: dict[str, str] = {
        "created_at":   str(result.get("created_at", "")),
        "fingerprint":  str(result.get("fingerprint", "")),
        "salt":         salt_hex,
        "password_hash": pw_hash,
    }

    # 4) role ごとにサマリ複製
    if role == "staff":
        # MunicipalStaffs: PK=staff_id, SK=municipality
        _copy_to(staff_tbl, {
            "staff_id":    str(username),
            "municipality": str(data.get("municipality", "")),
            **summary_common,
        })
    elif role == "admin":
        # AdminsTable: PK=admin_id, SK=session_id
        _copy_to(admin_tbl, {
            "admin_id":   str(username),
            "session_id": "PROFILE",
            **summary_common,
        })

    # 5) 結果をそのまま返却
    return result
