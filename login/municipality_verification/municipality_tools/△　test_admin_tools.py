# admin_tools/test_admin_tools.py
# test_admin_tools.py の最初に追加する
import os
os.environ["JWT_SECRET"] = "test_jwt_secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ADMIN_TABLE"] = "MunicipalAdmins"
os.environ["APPROVAL_LOG_TABLE"] = "MunicipalApprovalLogTable"
os.environ["AWS_REGION"] = "us-east-1"

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import boto3
import jwt
import uuid
from datetime import datetime, timedelta
from time import sleep

from admin_tools.approval_logger import log_approval
from admin_tools.jwt_utils import verify_admin_jwt
from admin_tools.register_admin import (
    register_admin, generate_salt, hash_password
)

@pytest.fixture(scope="session")
def dynamodb_client():
    return boto3.client("dynamodb", region_name=AWS_REGION)

@pytest.fixture(scope="session")
def dynamodb_resource():
    return boto3.resource("dynamodb", region_name=AWS_REGION)

# =========================================================================
# テスト開始
# =========================================================================

def test_register_admin(dynamodb_resource):
    """
    register_admin 関数を使って MunicipalAdminsTest テーブルに管理者を登録し、
    正しく反映されているか確認する。
    """
    admin_id = "test-admin-" + str(uuid.uuid4())[:8]
    password = "secret-password"
    name = "テスト職員"
    municipality = "テスト市"

    # 管理者登録
    register_admin(admin_id, password, name, municipality)

    # DynamoDB 確認
    table = dynamodb_resource.Table(ADMIN_TABLE)
    response = table.get_item(Key={"admin_id": admin_id, "municipality": municipality})
    item = response.get("Item", {})
    assert item["admin_id"] == admin_id
    assert item["name"] == name
    assert item["municipality"] == municipality
    assert "password_hash" in item
    assert "salt" in item

def test_log_approval(dynamodb_resource):
    """
    log_approval 関数を用いて MunicipalApprovalLogTable にログを記録し、
    正しく保存されることを確認。
    """
    uuid_user = "test-user-" + str(uuid.uuid4())[:8]
    action = "approved"
    approver_id = "admin-123"
    reason = "テスト理由"
    client_ip = "127.0.0.1"

    log_approval(uuid_user, action, approver_id, reason, client_ip)

    # DynamoDB 確認
    log_table = dynamodb_resource.Table(APPROVAL_LOG_TABLE)
    # log_id = f"{uuid_user}_{datetime.utcnow().isoformat()}" の形だが、
    # 厳密に同一文字列を取得するのは難しいので、Scanで探す
    items = log_table.scan()["Items"]
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
    assert len(s1) == 32  # 16バイトのhex=32文字
    assert len(s2) == 32
    assert s1 != s2

    # 同じソルトで同じパスワードなら同じ結果
    p1 = hash_password("mypassword", s1)
    p2 = hash_password("mypassword", s1)
    assert p1 == p2

def test_verify_admin_jwt_valid():
    """
    JWTが有効な場合、admin_id を正しく取得できるか。
    """
    # 実際には jwt_utils.py が JWT_SECRET, JWT_ALGORITHM を取得している
    # ここでは直接生成して呼び出す
    payload = {
        "admin_id": "jwt-admin-01",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    admin_id = verify_admin_jwt(token)
    assert admin_id == "jwt-admin-01"

def test_verify_admin_jwt_expired():
    """
    有効期限切れトークンの場合 None が返るか。
    """
    payload = {
        "admin_id": "expired-admin",
        "exp": datetime.utcnow() - timedelta(minutes=1)  # 期限切れ
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    admin_id = verify_admin_jwt(token)
    assert admin_id is None
