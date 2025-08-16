# municipality_registration/service.py
"""
市町村レコード登録 ＆ region_tree.json への追記ロジック
（対応する市町村管理者レコードも ADMIN_TABLE に作成）
"""
import os
import sys
import uuid
import logging
import hashlib
from datetime import datetime

# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from boto3.dynamodb.conditions import Key
from municipality_registration.config import (
    AWS_REGION,
    MUNICIPALITY_TABLE,
    STAFF_TABLE,
)
from municipality_registration.region_tree_updater import update_region_tree

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB テーブル準備

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
muni_tb  = dynamodb.Table(MUNICIPALITY_TABLE)
staff_tb = dynamodb.Table(STAFF_TABLE)

def _hash_password(password: str, salt: str) -> str:
    """SHA-256(salt + password) → hex"""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def register_municipality(payload: dict) -> dict:
    """
    payload 必須キー:
      continent, country_code, country_name,
      pref_code,    pref_name,
      municipality_name,
      staff_email,  staff_password

    戻り値:
      { success: True, municipality_id: ..., staff_id: ... }
    """
    # 1) 必須フィールドチェック
    required = [
        "continent",
        "country_code",
        "country_name",
        "pref_code",
        "pref_name",
        "municipality_name",
        "staff_email",
        "staff_password",
    ]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    # 2) 重複チェック（大陸 + 市町村一意）
    idx_expr = Key("continent").eq(payload["continent"]) & Key("municipality_name").eq(payload["municipality_name"])
    try:
        # まず GSI を使って照会
        dup = muni_tb.query(
            IndexName="continent-muni-index",
            KeyConditionExpression=idx_expr,
            Limit=1
        )
        if dup.get("Items"):
            raise ValueError("municipality already registered")
    except muni_tb.meta.client.exceptions.ResourceNotFoundException:
        # GSI が存在しない（または削除されている）場合は scan でフォールバック
        scan = muni_tb.scan(
            FilterExpression=Key("continent").eq(payload["continent"]) &
                             Key("municipality_name").eq(payload["municipality_name"])
        )
        if scan.get("Items"):
            raise ValueError("municipality already registered")

    # 3) Municipalities テーブルに書き込み
    municipality_id = "muni-" + uuid.uuid4().hex[:10]
    now_iso = datetime.utcnow().isoformat()
    muni_tb.put_item(
        Item={
            "municipality_id": municipality_id,
            "continent": payload["continent"],
            "country_code": payload["country_code"],
            "country_name": payload["country_name"],
            "pref_code": payload["pref_code"],
            "pref_name": payload["pref_name"],
            "municipality_name": payload["municipality_name"],
            "created_at": now_iso,
        }
    )

    # 4) MunicipalStaffs テーブルに書き込み
    staff_id = "staff-" + uuid.uuid4().hex[:8]
    salt = uuid.uuid4().hex
    pwd_hash = _hash_password(payload["staff_password"], salt)
    staff_tb.put_item(
        Item={
            "staff_id": staff_id,
            "municipality": municipality_id,
            "email": payload["staff_email"],
            "password_hash": pwd_hash,
            "salt": salt,
            "created_at": now_iso,
        }
    )

    # 5) region_tree.json へ追記
    update_region_tree(
        continent=payload["continent"],
        country_code=payload["country_code"],
        country_name=payload["country_name"],
        pref_code=payload["pref_code"],
        pref_name=payload["pref_name"],
        city_name=payload["municipality_name"],
    )

    logger.info(
        "Registered municipality %s (ID=%s) under %s/%s/%s",
        payload["municipality_name"],
        municipality_id,
        payload["continent"],
        payload["country_code"],
        payload["pref_code"],
    )

    return {
        "success": True,
        "municipality_id": municipality_id,
        "staff_id": staff_id,
    }
