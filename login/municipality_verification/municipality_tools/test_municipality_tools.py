# municipality_verification/municipality_tools/test_municipality_tools.py

import os
import sys
import uuid
import pytest
import boto3
import jwt
from datetime import datetime, timedelta

from login.login_app.routes.staff_routes import staff_register

# ─── 環境変数をテストの最上部で設定 ─────────────────────────────────
os.environ["JWT_SECRET"] = "test_jwt_secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["STAFF_TABLE"] = "MunicipalStaffs"
os.environ["APPROVAL_LOG_TABLE"] = "MunicipalApprovalLogTable"
os.environ["AWS_REGION"] = "us-east-1"

# ─── テスト対象モジュールを参照できるようにパスを調整 ───────────────────────────
# 「..」で municipality_verification を指し示す
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from login.login_app.account_manager.config import STAFF_TABLE
from municipality_tools.municipality_approval_logger import log_approval
from municipality_tools.municipality_jwt_utils     import verify_staff_jwt
from municipality_tools.municipality_register      import (
    register_staff, generate_salt, hash_password
)

# テスト内でも同様に使うため、グローバル変数に再定義
AWS_REGION         = os.getenv("AWS_REGION", "us-east-1")
STAFF_TABLE  = os.getenv("STAFF_TABLE", "MunicipalStaffs")
APPROVAL_LOG_TABLE = os.getenv("APPROVAL_LOG_TABLE", "MunicipalApprovalLogTable")
JWT_SECRET         = os.getenv("JWT_SECRET", "test_jwt_secret")
JWT_ALGORITHM      = os.getenv("JWT_ALGORITHM", "HS256")


@pytest.fixture(scope="session")
def dynamodb_client():
    return boto3.client("dynamodb", region_name=AWS_REGION)


@pytest.fixture(scope="session")
def dynamodb_resource():
    return boto3.resource("dynamodb", region_name=AWS_REGION)


def test_register_staff(dynamodb_resource):
    """
    register_staff 関数を使って MunicipalStaffs テーブルに管理者を登録し、
    正しく反映されているか確認する。
    """
    staff_id = "test-staff-" + str(uuid.uuid4())[:8]
    password = "secret-password"
    name = "テスト職員"
    municipality = "テスト市"

    # 管理者登録
    register_staff(staff_id, password, name, municipality)

    # DynamoDB から取得
    table = dynamodb_resource.Table(STAFF_TABLE)
    response = table.get_item(Key={"staff_id": staff_id, "municipality": municipality})
    item = response.get("Item", {})
    assert item["staff_id"] == staff_id
    assert item["name"] == name
    assert item["municipality"] == municipality
    assert "password_hash" in item
    assert "salt" in item


def test_log_approval(dynamodb_resource):
    """
    log_approval 関数を用いて MunicipalApprovalLogTable にログを記録し、
    正しく保存されることを確認する。
    """
    uuid_user = "test-user-" + str(uuid.uuid4())[:8]
    action = "approved"
    approver_id = "staff-123"
    reason = "テスト理由"
    client_ip = "127.0.0.1"

    # 承認ログ記録
    log_approval(uuid_user, action, approver_id, reason, client_ip)

    # DynamoDB から Scan して該当ログを探す
    log_table = dynamodb_resource.Table(APPROVAL_LOG_TABLE)
    items = log_table.scan().get("Items", [])
    found = False

    for it in items:
        if it.get("uuid") == uuid_user and it.get("action") == action:
            found = True
            assert it["approver_id"] == approver_id
            assert it["reason"] == reason
            assert it["client_ip"] == client_ip
            break

    assert found, "log_approval によるログが見つかりません"


def test_generate_salt_and_hash():
    """
    ソルト生成・ハッシュの単体テスト。
    """
    s1 = generate_salt()
    s2 = generate_salt()
    # 16 バイトの hex → 32 文字になる
    assert len(s1) == 32
    assert len(s2) == 32
    assert s1 != s2

    # 同じソルトで同じパスワードなら同じハッシュになる
    p1 = hash_password("mypassword", s1)
    p2 = hash_password("mypassword", s1)
    assert p1 == p2


def test_verify_staff_jwt_valid():
    """
    JWT が有効な場合、staff_id を正しく取得できるか。
    """
    payload = {
        "staff_id": "jwt-staff-01",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    staff_id = verify_staff_jwt(token)
    assert staff_id == "jwt-staff-01"


def test_verify_staff_jwt_expired():
    """
    有効期限切れ JWT の場合、None が返るか。
    """
    payload = {
        "staff_id": "expired-staff",
        "exp": datetime.utcnow() - timedelta(minutes=1)  # 既に期限切れ
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    staff_id = verify_staff_jwt(token)
    assert staff_id is None
