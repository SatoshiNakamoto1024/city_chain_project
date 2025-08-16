# municipality_verification/test_municipality_verification.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import boto3
import uuid
from datetime import datetime
from flask import Flask

# municipality_registration モジュールを呼び出して「市町村登録 & スタッフ登録」を行う
from municipality_registration.service import register_municipality

# ログインと承認フローをテストするパーツを import
from municipality_verification.municipality_login import staff_login_bp
from municipality_verification.views import municipality_verify_bp
from municipality_verification.verification import users_table

# 環境変数からテーブル名/リージョンを取得
AWS_REGION        = os.getenv("AWS_REGION", "us-east-1")
MUNICIPALIY_TABLE = os.getenv("MUNICIPALITY_TABLE", "Municipalities")
STAFF_TABLE       = os.getenv("STAFF_TABLE", "MunicipalStaffs")
DYNAMODB_TABLE    = os.getenv("USERS_TABLE", "UsersTable")
APPROVAL_LOG_TABLE= os.getenv("APPROVAL_LOG_TABLE", "MunicipalApprovalLogTable")


@pytest.fixture(scope="session")
def dynamodb_client():
    return boto3.client("dynamodb", region_name=AWS_REGION)


@pytest.fixture(scope="session")
def dynamodb_resource():
    return boto3.resource("dynamodb", region_name=AWS_REGION)


@pytest.fixture
def test_app():
    """
    Flask アプリを生成し、Blueprint を登録して TESTING モードで返す。
    テンプレートフォルダーは絶対パスで指定する必要あり。
    """
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
    app = Flask(__name__, template_folder=template_path)
    # /staff/login と /staff/verify を提供
    app.register_blueprint(staff_login_bp,        url_prefix="/staff")
    app.register_blueprint(municipality_verify_bp, url_prefix="/staff/verify")
    app.config["TESTING"] = True
    return app


def test_full_verification_flow(dynamodb_resource, test_app):
    """
    1) municipality_registration の register_municipality を使って、
       - 新しい市町村レコード (Municipalities) を作成
       - その結果、MunicipalStaffs に staff_id が作成される
    2) その staff_id + password で /staff/login を叩いて JWT を取得
    3) pending 状態のユーザーを UsersTable に直接書き込む
    4) /staff/verify (POST) へ JWT をつけて承認操作を行う
    5) DynamoDB を確認し、approval_status が "approved" になっているか、
       かつ MunicipalApprovalLogTable にログが残っているか検証
    """

    # --- 1) 市町村登録 & 職員登録 (register_municipality を呼び出す) ---
    sample_payload = {
        "continent":         "TestContinent",
        "country_code":      "TC",
        "country_name":      "TestCountry",
        "pref_code":         "TP",
        "pref_name":         "TestPref",
        "municipality_name": "TestMuni-" + str(uuid.uuid4().hex[:6]),
        "staff_email":       "mayor@testmune.jp",
        "staff_password":    "staff-pass-123"
    }
    res = register_municipality(sample_payload)
    assert res["success"] is True

    # register_municipality の戻り値で staff_id がわかる
    staff_id       = res["staff_id"]
    municipality_id= res["municipality_id"]
    # staff_password は sample_payload["staff_password"]

    # --- 2) /staff/login で JWT 取得 ---
    client = test_app.test_client()
    login_resp = client.post(
        "/staff/login",
        json={
            "staff_id":    staff_id,
            "password":    sample_payload["staff_password"],
            "municipality": municipality_id
        }
    )
    assert login_resp.status_code == 200
    login_data = login_resp.get_json()
    assert login_data["success"] is True
    token = login_data["jwt"]
    assert token is not None

    # --- 3) pending ユーザーを UsersTable に直接登録 ---
    test_user_uuid = "user-" + str(uuid.uuid4())[:8]
    users_table.put_item(Item={
        "uuid":            test_user_uuid,
        "session_id":      "REGISTRATION",          # テーブルの主キー
        "approval_status": "pending",
        "created_at":      datetime.utcnow().isoformat() + "Z"
    })

    # pending ユーザーが登録されたことを確認
    user_tbl = dynamodb_resource.Table(DYNAMODB_TABLE)
    resp_item = user_tbl.get_item(Key={"uuid": test_user_uuid, "session_id": "REGISTRATION"})
    assert "Item" in resp_item
    assert resp_item["Item"]["approval_status"] == "pending"

    # --- 4) /staff/verify (POST) に JWT をつけて承認 ---
    headers = {"Authorization": f"Bearer {token}"}
    form_data = {
        "uuid":   test_user_uuid,
        "action": "approve"
    }
    verify_resp = client.post("/staff/verify/", headers=headers, json=form_data)
    assert verify_resp.status_code == 200
    text = verify_resp.get_data(as_text=True)
    assert f"ユーザー {test_user_uuid} を承認しました" in text

    # --- 5) DynamoDB 確認：approval_status が "approved" になっていること ---
    updated_resp = user_tbl.get_item(Key={"uuid": test_user_uuid, "session_id": "REGISTRATION"})
    updated_item = updated_resp.get("Item", {})
    assert updated_item.get("approval_status") == "approved"

    # 承認ログが MunicipalApprovalLogTable に残っているか確認
    log_tbl = dynamodb_resource.Table(APPROVAL_LOG_TABLE)
    logs = log_tbl.scan().get("Items", [])
    found = False
    for it in logs:
        if it.get("uuid") == test_user_uuid and it.get("action") == "approve":
            found = True
            assert it["approver_id"] == staff_id
            break
    assert found, "承認ログが MunicipalApprovalLogTable に見つかりません"

    print("[✓] test_full_verification_flow 完了 - 一連の承認フローが正しく動作しました。")
