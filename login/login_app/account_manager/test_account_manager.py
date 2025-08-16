# account_manager/test_account_manager.py
"""
account_manager だけを検証する本番 DynamoDB 用テスト
--------------------------------------------------
* 登録 → サマリ行存在 → login 成功 だけを見る
* registration.register_user は monkeypatch で超軽量スタブ
* 本番テーブルに書き込み → テスト末尾でクリーンアップ
"""

import os, sys, uuid, pytest, boto3, logging
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from login_app.account_manager.config import (
    AWS_REGION, USERS_TABLE, STAFF_TABLE, ADMIN_TABLE
)
from login_app.account_manager.app_account_manager import (
    create_account, login
)

logging.basicConfig(level=logging.INFO)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_tbl  = dynamodb.Table(USERS_TABLE)
staff_tbl  = dynamodb.Table(STAFF_TABLE)
admin_tbl  = dynamodb.Table(ADMIN_TABLE)

# ---------------------------------------------------------------- fixture: 軽量 register_user
@pytest.fixture(autouse=True)
def stub_register_user(monkeypatch):
    from datetime import timezone
    def fake_register_user(payload):
        return {
            "uuid":        str(uuid.uuid4()),
            "username":    payload["username"],
            "created_at":  datetime.now(timezone.utc).isoformat(),
            "fingerprint": "00:11:22",
        }
    monkeypatch.setattr(
        "login_app.account_manager.register_account.register_user",
        fake_register_user
    )
    yield  # 後始末は不要

# ---------------------------------------------------------------- helper
def _del(table, key):
    try:
        table.delete_item(Key=key)
    except Exception:
        pass

# ---------------------------------------------------------------- tests
@pytest.mark.parametrize("role,target_tbl,key_names", [
    ("staff", STAFF_TABLE,  ("staff_id", "municipality")),
    ("admin", ADMIN_TABLE,  ("admin_id", "session_id")),
])
def test_create_and_login(role, target_tbl, key_names):
    suffix = uuid.uuid4().hex[:6]
    username = f"{role}_{suffix}"
    muni_id  = f"MU-{suffix}"

    payload = {
        "role": role,
        "username": username,
        "password": "Pw123!",
    }
    if role == "staff":
        payload.update({"municipality":"テスト市","municipality_id":muni_id})

    # ---- create
    res = create_account(payload)
    uid = res["uuid"]

    tbl = dynamodb.Table(target_tbl)
    if role == "staff":
        # staff_id=<username>, municipality=<テスト市> で検索
        key = {
            "staff_id":    username,
            "municipality": payload["municipality"],
        }
    else:
        # admin_id=<username>, session_id="PROFILE"
        key = {
            key_names[0]: username,
            key_names[1]: "PROFILE",
        }
    assert tbl.get_item(Key=key).get("Item"), "summary row missing"

    # ---- login
    assert login({"role":role,"username":username,"password":"Pw123!"})["success"]

    # ---- cleanup
    _del(tbl, key)
    for session in ("REGISTRATION","USER_PROFILE"):
        _del(users_tbl, {"uuid":uid,"session_id":session})
