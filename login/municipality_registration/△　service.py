# municipality_registration/service.py
"""
市町村レコード登録 ＆ region_tree.json 更新ロジック
（対応する市町村管理者レコードも ADMIN_TABLE に作成）
"""
import os
import sys
import json
import uuid
import logging
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from boto3.dynamodb.conditions import Key
from municipality_registration.config import (
    AWS_REGION,
    MUNICIPALITY_TABLE,
    ADMIN_TABLE,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ───────── DynamoDB テーブル ─────────
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
muni_tb = dynamodb.Table(MUNICIPALITY_TABLE)
admin_tb = dynamodb.Table(ADMIN_TABLE)

# ───────── region_tree.json パス ─────────
REGION_JSON = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "..",
    "municipality_verification",
    "mapping_continental_municipality",
    "region_tree.json",
)

# --------------------------------------------------
def _load_region() -> dict:
    pj = Path(REGION_JSON)
    if not pj.exists():
        pj.write_text("{}", encoding="utf-8")
    return json.loads(pj.read_text(encoding="utf-8"))


def _save_region(data: dict):
    Path(REGION_JSON).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _hash_password(password: str, salt: str) -> str:
    """SHA-256(salt + password)"""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# --------------------------------------------------
# region_tree.json に基づく 4 階層バリデーション
# --------------------------------------------------
def _validate_hierarchy(payload: dict) -> None:
    """
    continent → country → prefecture → city の順に
    region_tree.json に存在するかを確認。
    """
    tree = _load_region()

    cont = tree.get(payload["continent"])
    if not cont:
        raise ValueError(f"invalid continent: {payload['continent']}")

    country = next(
        (c for c in cont["countries"] if c["code"] == payload["country_code"]), None
    )
    if not country:
        raise ValueError(
            f"country_code not found under continent: {payload['country_code']}"
        )

    pref = next(
        (p for p in country["prefectures"] if p["code"] == payload["pref_code"]), None
    )
    if not pref:
        raise ValueError(
            f"pref_code not found under country: {payload['pref_code']}"
        )

    if payload["municipality_name"] not in pref["cities"]:
        raise ValueError(
            f"municipality_name not found under pref: {payload['municipality_name']}"
        )


# --------------------------------------------------
def register_municipality(payload: dict) -> dict:
    """
    Parameters (all required):
        continent, country_code, country_name,
        pref_code, pref_name,
        municipality_name,
        admin_email, admin_password

    Returns:
        { success: True, municipality_id: ..., admin_id: ... }
    """
    required = [
        "continent",
        "country_code",
        "country_name",
        "pref_code",
        "pref_name",
        "municipality_name",
        "admin_email",
        "admin_password",
    ]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    # 4 階層で存在チェック
    _validate_hierarchy(payload)

    # ─── 重複チェック（大陸 + 市町村でユニークと仮定）────
    idx_expr = Key("continent").eq(payload["continent"]) & Key(
        "municipality_name"
    ).eq(payload["municipality_name"])

    try:
        dup = muni_tb.query(
            IndexName="continent-muni-index", KeyConditionExpression=idx_expr, Limit=1
        )
        if dup.get("Items"):
            raise ValueError("municipality already registered")
    except muni_tb.meta.client.exceptions.ValidationException:
        # インデックスが無ければ scan
        scan = muni_tb.scan(
            FilterExpression=Key("continent").eq(payload["continent"])
            & Key("municipality_name").eq(payload["municipality_name"])
        )
        if scan.get("Items"):
            raise ValueError("municipality already registered")

    # ─── DynamoDB: Municipalities ───
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

    # ─── DynamoDB: MunicipalAdmins ───
    admin_id = "admin-" + uuid.uuid4().hex[:8]
    salt = uuid.uuid4().hex
    pwd_hash = _hash_password(payload["admin_password"], salt)

    admin_tb.put_item(
        Item={
            "admin_id": admin_id,
            "municipality": municipality_id,
            "email": payload["admin_email"],
            "password_hash": pwd_hash,
            "salt": salt,
            "created_at": now_iso,
        }
    )

    # ─── region_tree.json へアップサート（無ければ自動追加）────
    reg = _load_region()
    cont_obj = reg.setdefault(payload["continent"], {"countries": []})

    # country
    cntry = next(
        (c for c in cont_obj["countries"] if c["code"] == payload["country_code"]), None
    )
    if not cntry:
        cntry = {
            "code": payload["country_code"],
            "name": payload["country_name"],
            "prefectures": [],
        }
        cont_obj["countries"].append(cntry)

    # prefecture
    pref = next(
        (p for p in cntry["prefectures"] if p["code"] == payload["pref_code"]), None
    )
    if not pref:
        pref = {
            "code": payload["pref_code"],
            "name": payload["pref_name"],
            "cities": [],
        }
        cntry["prefectures"].append(pref)

    # city
    city = payload["municipality_name"]
    if city not in pref["cities"]:
        pref["cities"].append(city)

    _save_region(reg)
    logger.info("region_tree.json updated for %s", city)

    return {
        "success": True,
        "municipality_id": municipality_id,
        "admin_id": admin_id,
    }
