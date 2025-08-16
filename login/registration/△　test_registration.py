# tests/test_registration.py
# -*- coding: utf-8 -*-
"""
pytest 用   integration‐test  (本番 PEM 運用版)
------------------------------------------------
* 2025‑04‑27 : 旧 JSON 登録 → PEM 登録 + client_cert_fp 必須 に対応
* ルート構成
    - POST /registration/           : 新規登録 / 追加端末（qr_code 有無で分岐）
    - POST /registration/pairing_token : ペアリングトークン発行（username / password / client_cert_fp）

このテストはローカルに立ち上げた dev‑server (127.0.0.1:5000) を前提にする。
DynamoDB は "UsersTable" / "DevicesTable" を用意済みであること。
"""

import os
import sys
import json
import base64
import uuid
import hashlib
import time
import requests
import boto3
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Python パス設定
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from registration.config import AWS_REGION
from auth_py.fingerprint import normalize_fp          # 指紋正規化ユーティリティ

# ---------------------------------------------------------------------------
# 固定 URL
# ---------------------------------------------------------------------------
BASE_URL      = "http://127.0.0.1:5000"
REG_URL       = f"{BASE_URL}/registration/"             # 新規登録／追加端末 共通
TOKEN_URL     = f"{BASE_URL}/registration/pairing_token"  # ペアリングトークン発行
ADD_DEV_URL   = REG_URL                                # ★ qr_code を投げるのは /registration/ （追加端末分岐）

# ---------------------------------------------------------------------------
# DynamoDB ヘルパ
# ---------------------------------------------------------------------------
dynamodb      = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table   = dynamodb.Table("UsersTable")
devices_table = dynamodb.Table("DevicesTable")

# ---------------------------------------------------------------------------
# DynamoDB クリーンアップ関数
# ---------------------------------------------------------------------------

def _scan_and_delete(table, filter_kw):
    last = None
    while True:
        if last:
            filter_kw["ExclusiveStartKey"] = last
        resp = table.scan(**filter_kw)
        for item in resp.get("Items", []):
            # key_schema = [{"AttributeName":"uuid","KeyType":"HASH"}, ...]
            key_map = {e["AttributeName"]: item[e["AttributeName"]] for e in table.key_schema}
            table.delete_item(Key=key_map)
        last = resp.get("LastEvaluatedKey")
        if not last:
            break

def cleanup_user(username: str):
    _scan_and_delete(
        users_table,
        {
            "FilterExpression": "#u = :u",
            "ExpressionAttributeNames": {"#u": "username"},
            "ExpressionAttributeValues": {":u": username},
        },
    )


def cleanup_devices(uuid_val: str):
    _scan_and_delete(
        devices_table,
        {
            "FilterExpression": "#u = :u",
            "ExpressionAttributeNames": {"#u": "uuid"},
            "ExpressionAttributeValues": {":u": uuid_val},
        },
    )

# ---------------------------------------------------------------------------
# PEM / Fingerprint ヘルパ
# ---------------------------------------------------------------------------

def calc_fp_from_pem(pem_str: str) -> str:
    """PEM 文字列 → sha256 → normalize"""
    sha = hashlib.sha256(pem_str.encode()).hexdigest()
    return normalize_fp(sha)

# ---------------------------------------------------------------------------
# 登録ユーティリティ
# ---------------------------------------------------------------------------

def primary_register():
    """1 台目（親機）を登録してテスト用情報を返す"""

    username = "it_parent_" + uuid.uuid4().hex[:6]
    cleanup_user(username)

    payload = {
        "username": username,
        "email":    "parent@example.com",
        "password": "TestPass123!",
        "name":     "Primary User",
        "birth_date": "2000-01-01",
        "address":    "Primary Street",
        "mynumber":   "987654321098",
        "phone":      "08011112222",
        "initial_harmony_token": "100",
        # ★ PEM はサーバーで生成して貰う → ここでは渡さない
    }

    r = requests.post(REG_URL, json=payload)
    assert r.status_code == 200, f"reg failed {r.status_code}"
    body = r.json()
    assert body["success"] is True

    return {
        "username":    username,
        "password":    payload["password"],
        "uuid":        body["uuid"],
        "fingerprint": body["fingerprint"],
        "client_cert": body["client_cert"],
    }

import time                                     # ← 追加
RETRY = 10       # 最大 6 回 (= 約 12 秒)
SLEEP = 2     # 2 秒ずつ待つ
time.sleep(2)

def issue_pairing_token(username: str, password: str, fp: str):
    """ /registration/pairing_token をリトライ付きで呼ぶ """
    req_body = {
        "username":       username,
        "password":       password,
        "client_cert_fp": fp if isinstance(fp, str) else normalize_fp(fp)
    }
    last_resp = None
    for _ in range(RETRY):
        last_resp = requests.post(TOKEN_URL, json=req_body)
        if last_resp.status_code == 200:
            break
        time.sleep(SLEEP)

    assert last_resp is not None and last_resp.status_code == 200, \
        f"token issue failed {last_resp.status_code}"
    data = last_resp.json()
    assert "device_token" in data and "uuid" in data

    qr_b64 = base64.b64encode(json.dumps(data).encode()).decode()
    return data, qr_b64


def register_secondary(qr_b64: str, username: str, password: str, device_name="SecDevice"):
    """/registration/ に QR(Base64) と認証情報を送って 2 台目登録"""
    payload = {
        "qr_code": qr_b64,
        "device_name": device_name,
        "username": username,
        "password": password,
    }
    r = requests.post(ADD_DEV_URL, json=payload)
    assert r.status_code == 200, f"add_device failed {r.status_code}"
    body = r.json()
    assert body["success"] is True
    return body

# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------

def test_get_register_html():
    res = requests.get(REG_URL)
    assert res.status_code == 200
    assert "ユーザー登録" in res.text


def test_primary_registration_and_cert():
    info = primary_register()

    # PEM の整合性
    pem = base64.b64decode(info["client_cert"]).decode()
    assert "BEGIN CERTIFICATE" in pem

    fp_calc = calc_fp_from_pem(pem)
    assert fp_calc == normalize_fp(info["fingerprint"])


def test_pairing_token_flow_and_add_device():
    # ------- 親機登録 -------
    # primary デバイスは pairing_token 発行に必要なので消さない
    info = primary_register()
    time.sleep(2)  # ✅ここで待つ！
    
    uuid_primary = info["uuid"]
    
    # ------- ペアリングトークン発行 -------
    token_obj, qr_b64 = issue_pairing_token(info["username"], info["password"], info["fingerprint"])

    # ------- 2 台目登録 -------
    add_result = register_secondary(qr_b64, info["username"], info["password"],
                                    device_name="IT_Secondary")
    assert add_result["uuid"] == uuid_primary
    # 1 台目と 2 台目の指紋は必ず異なる
    assert add_result["fingerprint"] != info["fingerprint"]

    # DevicesTable にレコードが出来ているか
    # uuid=primary と uuid=新 device_id が両方あるはず
    scan = devices_table.scan(
        FilterExpression="#u = :u",
        ExpressionAttributeNames={"#u": "uuid"},
        ExpressionAttributeValues={":u": uuid_primary},
        ConsistentRead=True
    )
    assert len(scan["Items"]) >= 2          # primary ＋ secondary
    assert any(i["device_id"] == add_result["device_id"] for i in scan["Items"])


def test_pairing_token_invalid_or_tampered():
    info = primary_register()
    time.sleep(2)  # ✅ここで待つ！
    
    token_obj, qr_b64 = issue_pairing_token(info["username"], info["password"], info["fingerprint"])

    # ---- 1) 期限切れを模倣：expires_at を過去に書き換え ----
    bad = json.loads(base64.b64decode(qr_b64))
    bad["expires_at"] = int(time.time()) - 10
    qr_bad_b64 = base64.b64encode(json.dumps(bad).encode()).decode()

    r1 = requests.post(ADD_DEV_URL, json={
        "qr_code": qr_bad_b64,
        "device_name": "ExpiredDevice",
        "username": info["username"],
        "password": info["password"],
    })
    assert r1.status_code in (400, 401, 500)

    # ---- 2) デバイストークンを改竄 ----
    bad2 = json.loads(base64.b64decode(qr_b64))
    bad2["device_token"] = uuid.uuid4().hex
    qr_bad2_b64 = base64.b64encode(json.dumps(bad2).encode()).decode()

    r2 = requests.post(ADD_DEV_URL, json={
        "qr_code": qr_bad2_b64,
        "device_name": "TamperedDevice",
        "username": info["username"],
        "password": info["password"],
    })
    assert r2.status_code in (400, 401, 500)


def test_registration_post_validation_errors():
    # ボディ無し
    r = requests.post(REG_URL)
    assert r.status_code == 400
    assert "error" in r.json()

    # 必須欠落
    r2 = requests.post(REG_URL, json={"username": "x"})
    assert r2.status_code in (400, 500)
    assert "error" in r2.json()
